from pydantic import BaseModel

from alphabet.schemas.common import AgentName, Horizon


class AgentWeights(BaseModel):
    financial: float = 0.30
    chart: float = 0.25
    macro: float = 0.20
    news: float = 0.25

    def as_dict(self) -> dict[AgentName, float]:
        return {
            AgentName.FINANCIAL: self.financial,
            AgentName.CHART: self.chart,
            AgentName.MACRO: self.macro,
            AgentName.NEWS: self.news,
        }

    def normalized(self) -> dict[AgentName, float]:
        weights = self.as_dict()
        total = sum(weights.values())
        if total == 0:
            even = 1.0 / len(weights)
            return {name: even for name in weights}
        return {name: value / total for name, value in weights.items()}


def default_weights_for_horizon(horizon: Horizon) -> AgentWeights:
    if horizon == Horizon.SHORT:
        return AgentWeights(financial=0.15, chart=0.35, macro=0.15, news=0.35)
    if horizon == Horizon.LONG:
        return AgentWeights(financial=0.45, chart=0.10, macro=0.30, news=0.15)
    return AgentWeights()
