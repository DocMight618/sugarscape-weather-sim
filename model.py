from pathlib import Path

import numpy as np

import mesa
from agents import SugarAgent
## Using OrthogonalVonNeumannGrid, which enforces cardinal (N/S/E/W) neighborhood
## lookups consistent with Epstein & Axtell's original specification
from mesa.discrete_space import OrthogonalVonNeumannGrid
from mesa.discrete_space.property_layer import PropertyLayer


class SugarScapeModel(mesa.Model):
    """
    SugarScape model (Epstein & Axtell 1996) extended with stochastic extreme
    weather events. Weather events are spatially localized, temporary reductions
    in sugar availability that strike random grid locations each step with a
    user-defined probability.

    Research question: How does the frequency of extreme weather events affect
    long-run population size and wealth inequality (Gini coefficient)?
    """

    # ------------------------------------------------------------------
    # DATA COLLECTION REPORTERS
    # ------------------------------------------------------------------

    def calc_gini(self):
        """
        Compute the Gini coefficient over current agent sugar holdings.
        Returns 0 if no agents remain (avoids division-by-zero on collapse).
        Used by DataCollector every step.
        """
        agent_sugars = [a.sugar for a in self.agents]
        if not agent_sugars or sum(agent_sugars) == 0:
            return 0
        sorted_sugars = sorted(agent_sugars)
        n = len(sorted_sugars)
        x = sum(el * (n - ind) for ind, el in enumerate(sorted_sugars)) / (
            n * sum(sorted_sugars)
        )
        return 1 + (1 / n) - 2 * x

    # [MODIFICATION] New reporter tracking living agent count each step,
    # allowing population dynamics to be plotted alongside the Gini coefficient.
    def calc_population(self):
        """Return the number of agents currently alive."""
        return len(self.agents)

    # ------------------------------------------------------------------
    # INITIALISATION
    # ------------------------------------------------------------------

    def __init__(
        self,
        width=50,
        height=50,
        initial_population=200,
        endowment_min=25,
        endowment_max=50,
        metabolism_min=1,
        metabolism_max=5,
        vision_min=1,
        vision_max=5,
        # [MODIFICATION] — Extreme weather parameters ——————————————————
        # weather_probability: per-step chance (0–1) a new event spawns.
        #   This is the primary independent variable for the research question.
        weather_probability=0.1,
        # weather_severity: sugar multiplier inside the affected region.
        #   0.0 = total resource destruction; 1.0 = no effect.
        weather_severity=0.2,
        # weather_duration: steps the suppression persists before expiring.
        #   Models the lasting impact of a drought, flood, or frost.
        weather_duration=5,
        # weather_radius: Euclidean radius (cells) of the affected circle.
        weather_radius=8,
        # ——————————————————————————————————————————————————————————————
        seed=None,
    ):
        super().__init__(rng=seed)

        # Core grid dimensions and run flag
        self.width = width
        self.height = height
        self.running = True

        # [MODIFICATION] Store weather parameters as instance variables so
        # step() and the helper methods can reference them without passing
        # arguments each call — consistent with Mesa model-state conventions.
        self.weather_probability = weather_probability
        self.weather_severity = weather_severity
        self.weather_duration = weather_duration
        self.weather_radius = weather_radius

        # [MODIFICATION] Registry of currently active weather events.
        # Each entry is a dict: {cx, cy, radius, severity, steps_left}.
        # Initialized empty; events are appended by _maybe_trigger_weather().
        self.active_weather_events = []

        # Orthogonal (von Neumann) grid — torus=False gives hard boundaries
        self.grid = OrthogonalVonNeumannGrid(
            (self.width, self.height), torus=False, random=self.random
        )

        # [MODIFICATION] DataCollector now reports both Gini and Population,
        # enabling simultaneous observation of distributional and demographic
        # outcomes — both outcomes of interest for the research question.
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Gini": self.calc_gini,
                "Population": self.calc_population,   # [MODIFICATION]
            }
        )

        # Load the static sugar-capacity map from the raster text file and
        # register it as a PropertyLayer on the grid.  This array also serves
        # as the ceiling for growback each step.
        self.sugar_distribution = np.genfromtxt(
            Path(__file__).parent / "sugar-map.txt"
        )
        self.grid.add_property_layer(
            PropertyLayer.from_data("sugar", self.sugar_distribution)
        )

        # Spawn agents at random cells with randomised traits drawn uniformly
        # from the supplied min/max ranges, per Epstein & Axtell Chapter II.
        SugarAgent.create_agents(
            self,
            initial_population,
            self.random.choices(self.grid.all_cells.cells, k=initial_population),
            sugar=self.rng.integers(
                endowment_min, endowment_max, (initial_population,), endpoint=True
            ),
            metabolism=self.rng.integers(
                metabolism_min, metabolism_max, (initial_population,), endpoint=True
            ),
            vision=self.rng.integers(
                vision_min, vision_max, (initial_population,), endpoint=True
            ),
        )

        # Collect baseline data before the first step
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # [MODIFICATION] EXTREME WEATHER HELPER METHODS
    # All three methods below are new additions to the base model.
    # ------------------------------------------------------------------

    def _maybe_trigger_weather(self):
        """
        [MODIFICATION] Stochastically spawn a new extreme weather event.

        At each step, draw a uniform random number.  If it is less than
        weather_probability, create a new event centred on a uniformly
        random grid cell.  Using a per-step Bernoulli draw means events
        are independent across time — no clustering or seasonality — which
        isolates the effect of raw frequency on model outcomes.
        """
        if self.random.random() < self.weather_probability:
            cx = self.random.randint(0, self.width - 1)
            cy = self.random.randint(0, self.height - 1)
            event = {
                "cx": cx,                          # event centre x-coordinate
                "cy": cy,                          # event centre y-coordinate
                "radius": self.weather_radius,     # spatial extent (cells)
                "severity": self.weather_severity, # sugar multiplier (lower = worse)
                "steps_left": self.weather_duration,  # countdown to expiry
            }
            self.active_weather_events.append(event)

    def _build_weather_suppression_mask(self):
        """
        [MODIFICATION] Build a grid-wide suppression multiplier from all
        currently active weather events.

        Algorithm:
          1. Start with a (width × height) array of 1.0 (no suppression).
          2. For each active event, compute Euclidean distance from every
             cell to the event centre using pre-built meshgrids (vectorised
             for performance on a 50×50 grid).
          3. For cells within the event radius, set the multiplier to the
             minimum of its current value and the event's severity.
             Taking the minimum means overlapping events compound at the
             worst (lowest) severity rather than averaging, which reflects
             the real-world intuition that concurrent disasters are not
             ameliorative.

        Returns:
            np.ndarray of shape (width, height) with values in [0, 1].
        """
        multiplier = np.ones((self.width, self.height), dtype=float)

        # Coordinate meshgrids computed once and shared across all events
        xs = np.arange(self.width)
        ys = np.arange(self.height)
        xx, yy = np.meshgrid(xs, ys, indexing="ij")

        for event in self.active_weather_events:
            dist = np.sqrt((xx - event["cx"]) ** 2 + (yy - event["cy"]) ** 2)
            in_radius = dist <= event["radius"]
            # Apply most-severe suppression where this event overlaps
            multiplier = np.where(
                in_radius,
                np.minimum(multiplier, event["severity"]),
                multiplier,
            )

        return multiplier

    def _tick_weather_events(self):
        """
        [MODIFICATION] Age all active weather events by one step and
        remove any that have expired (steps_left reaches 0).

        Using a list comprehension to filter-and-update in a single pass
        avoids mutation during iteration and keeps the event list compact.
        """
        self.active_weather_events = [
            {**e, "steps_left": e["steps_left"] - 1}
            for e in self.active_weather_events
            if e["steps_left"] > 1   # keep only events with time remaining
        ]

    # ------------------------------------------------------------------
    # STEP
    # ------------------------------------------------------------------

    def step(self):
        """
        Advance the model by one time step.

        Order of operations (original steps marked; modifications marked [M]):
          [M] 1. Possibly trigger a new extreme weather event.
              2. Grow sugar back by 1, capped at the static map maximum.
          [M] 3. Apply weather suppression mask to current sugar levels.
          [M] 4. Decrement and expire active weather event counters.
              5. Agents move, gather and eat, then die if sugar ≤ 0.
              6. Collect Gini and Population data.

        Note on step ordering: suppression is applied *after* growback so
        that the environment attempts to recover every step, but active
        weather events partially or fully cancel that recovery.  This allows
        the model to represent both events that merely slow recovery (high
        severity value) and those severe enough to reverse it (low severity).
        """
        # [MODIFICATION] Step 1: stochastically spawn a weather event
        self._maybe_trigger_weather()

        # Step 2: standard sugar growback (original model logic, unchanged)
        self.grid.sugar.data = np.minimum(
            self.grid.sugar.data + 1, self.sugar_distribution
        )

        # [MODIFICATION] Step 3: apply suppression from all active events.
        # Guard clause skips mask construction entirely when no events exist,
        # ensuring zero performance overhead in the weather_probability=0 case.
        if self.active_weather_events:
            multiplier = self._build_weather_suppression_mask()
            self.grid.sugar.data = self.grid.sugar.data * multiplier

        # [MODIFICATION] Step 4: age and expire weather events
        self._tick_weather_events()

        # Step 5: standard agent actions (original model logic, unchanged)
        self.agents.shuffle_do("move")
        self.agents.shuffle_do("gather_and_eat")
        self.agents.shuffle_do("see_if_die")

        # Step 6: collect Gini and Population for plotting
        self.datacollector.collect(self)
