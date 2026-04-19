# SugarScape with Extreme Weather Events

**Haoyan "Ken" Wang** — Midterm Exercise 1

## Research Questions

How do severe weather events affect population size and inequality in a given region? More specifically, what effects do the **frequency** and **duration** of weather events have on population size and inequality? This project uses the SugarScape model proposed by Epstein & Axtell (1996) to answer these questions.

## Hypotheses

**H1 (Baseline):** When there is no natural disaster (weather event probability `p = 0`), the population should stabilize at a certain point, and the Gini coefficient should also stabilize.

**H2:** When the probability of natural disaster is relatively low but the duration is high, the population decreases in a more volatile way, and the Gini coefficient is slightly lower than the baseline.

**H3:** When the probability of natural disaster is relatively high but the duration is low, the population reduces to a much smaller size than the initial population, and the Gini coefficient is more volatile than the baseline.

## Modification Description

`agents.py` was not modified. All modifications are in `model.py` and are noted in the inline comments. Four new parameters were added:

- **`weather_probability`** (float, 0–1): the per-step probability of a weather event occurring. Interpreted as the *frequency* of natural disasters and is the primary variable of interest.
- **`weather_severity`** (float, 0–1): a multiplier applied to current sugar levels in the affected area. At `0`, all sugar is destroyed; at `1`, sugar is unaffected.
- **`weather_duration`** (int, steps): the number of steps before sugar levels return to pre-event levels, simulating the delayed recovery caused by real-world disasters such as floods or tornadoes.
- **`weather_radius`** (int, cells): the spatial extent of the affected region.

## Relationship to the Base Model

The original SugarScape model describes a stable, reliable environment: sugar grows back at a steady rate and agents die only from insufficient consumption relative to their metabolism.

The modified version destabilizes this environment in three ways that make it more realistic:

1. **Two types of inequality.** The model now captures both *structural inequality* (driven by endowment and innate agent traits) and *shock-induced inequality* (driven by exposure to natural disasters), mirroring real-world distributional dynamics.
2. **A non-static environment.** There is always some probability of a natural disaster altering the amount of available resources, breaking the assumption of a temporally reliable landscape.
3. **Agents as resilient households.** Initial endowment now functions as a financial buffer, so agents come to represent individuals with different levels of resilience to external environmental shocks rather than just foragers with different cognitive and metabolic traits.

## Results

All experiments held other parameters constant with a small event radius (`r = 5`) to keep results interpretable.

| Hypothesis | `p` | Duration | Population stabilizes | Gini at stabilization |
|---|---|---|---|---|
| H1 (baseline) | 0.00 | — | ~100 steps, ~100 agents | ~0.33 |
| H2 | 0.20 | 15 steps | ~52 steps, ~100 agents | ~0.30 (rising trend after) |
| H3 | 0.75 | 5 steps | ~60 steps, smaller than H2 | Volatile, stabilizing trend after ~60 steps |

The results suggest that **large but infrequent natural disasters can be more devastating** than frequent but short ones: population in H3 declines faster initially and continues to slowly decrease even after apparent stabilization. Both H2 and H3 show that natural disasters can act as an **equalizer** — the Gini coefficient tends to be lower than the baseline after weather events occur, indicating a compression of wealth inequality.

## How to Run

```bash
solara run app.py
```

## Files

| File | Description |
|---|---|
| `agents.py` | Agent class (unmodified) |
| `model.py` | Model class with extreme weather modifications |
| `app.py` | Solara visualization and GUI sliders |
| `sugar-map.txt` | Raster file with default sugar distribution |

## Data Availability

All Python scripts are available on GitHub: [https://github.com/DocMight618/sugarscape-weather-sim](https://github.com/DocMight618/sugarscape-weather-sim)

## AI Use Declaration

Claude was used to help debug `model.py` and `app.py`. Stack Overflow was consulted for guidance on building the Solara GUI (sliders and interface layout).
