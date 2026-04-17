from model import SugarScapeModel
from mesa.visualization import Slider, SolaraViz, make_plot_component
from mesa.visualization.components.matplotlib_components import make_mpl_space_component
from mesa.visualization.components import AgentPortrayalStyle, PropertyLayerStyle

## Define agent portrayal (color, size, shape)
def agent_portrayal(agent):
    return AgentPortrayalStyle(
        color="red",
        marker="o",
        size=10,
    )

## Define map portrayal, with yellower squares having more sugar than white squares
def propertylayer_portrayal(layer):
    return PropertyLayerStyle(
        color="yellow", alpha=0.8, colorbar=True, vmin=0, vmax=10
    )

## Define model space component based on above
sugarscape_space = make_mpl_space_component(
    agent_portrayal=agent_portrayal,
    propertylayer_portrayal=propertylayer_portrayal,
    post_process=None,
    draw_grid=False,
)

## Define Gini and Population plots
GiniPlot = make_plot_component("Gini")
PopulationPlot = make_plot_component("Population")

## Define variable model parameters
model_params = {
    "seed": {
        "type": "InputText",
        "value": 42,
        "label": "Random Seed",
    },
    "width": 50,
    "height": 50,
    "initial_population": Slider(
        "Initial Population", value=200, min=50, max=500, step=10
    ),
    # Agent endowment parameters
    "endowment_min": Slider("Min Initial Endowment", value=25, min=5, max=30, step=1),
    "endowment_max": Slider("Max Initial Endowment", value=50, min=30, max=100, step=1),
    # Metabolism parameters
    "metabolism_min": Slider("Min Metabolism", value=1, min=1, max=3, step=1),
    "metabolism_max": Slider("Max Metabolism", value=5, min=3, max=8, step=1),
    # Vision parameters
    "vision_min": Slider("Min Vision", value=1, min=1, max=3, step=1),
    "vision_max": Slider("Max Vision", value=5, min=3, max=8, step=1),
    # --- Extreme Weather Parameters ---
    "weather_probability": Slider(
        "Weather Event Probability (per step)", value=0.1, min=0.0, max=1.0, step=0.05
    ),
    "weather_severity": Slider(
        "Weather Severity (sugar multiplier; lower = worse)", value=0.2, min=0.0, max=1.0, step=0.05
    ),
    "weather_duration": Slider(
        "Weather Duration (steps)", value=5, min=1, max=20, step=1
    ),
    "weather_radius": Slider(
        "Weather Radius (cells)", value=8, min=1, max=25, step=1
    ),
}

## Instantiate model
model = SugarScapeModel()

## Define all aspects of page
page = SolaraViz(
    model,
    components=[
        sugarscape_space,
        GiniPlot,
        PopulationPlot,
    ],
    model_params=model_params,
    name="Sugarscape with Extreme Weather",
    play_interval=150,
)
## Return page
page
