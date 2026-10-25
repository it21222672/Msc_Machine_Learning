"""SHAP helper that works for Random Forest, XGBoost, LightGBM and CatBoost classifiers."""
import numpy as np
import shap


def positive_class_shap(model, X):
    """Returns (shap_values for the 'spike' class as a 2-D array, base value).
    XGBoost / LightGBM / CatBoost values are in log-odds; Random Forest values are in probability."""
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X)
    if isinstance(sv, list):
        sv = sv[1]
    sv = np.asarray(sv)
    if sv.ndim == 3:
        sv = sv[:, :, 1]
    ev = np.atleast_1d(explainer.expected_value)
    base = float(ev[1] if len(ev) > 1 else ev[0])
    return sv, base


class SpikeExplainer:
    """Caches a SHAP TreeExplainer so the API can explain single predictions quickly."""
    def __init__(self, model):
        self.explainer = shap.TreeExplainer(model)
        ev = np.atleast_1d(self.explainer.expected_value)
        self.base = float(ev[1] if len(ev) > 1 else ev[0])

    def explain(self, X):
        sv = self.explainer.shap_values(X)
        if isinstance(sv, list):
            sv = sv[1]
        sv = np.asarray(sv)
        if sv.ndim == 3:
            sv = sv[:, :, 1]
        return sv
