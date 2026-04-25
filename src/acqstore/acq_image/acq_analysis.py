from enum import Enum

class AnalysisType(Enum):
    VELOCITY = "velocity"
    DIAMETER = "diameter"

class AcqAnalysis:
    def __init__(self):
        self._analysis = []

    def add_analysis(self, analysis: AnalysisType) -> None:
        self._analysis.append(analysis)

    def get_analysis(self) -> list[AnalysisType]:
        return self._analysis