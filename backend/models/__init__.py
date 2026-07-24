import os
import importlib.util

# Dynamically load PreEvalOutput and others from TIPSC-Agent to resolve shadowed import
_tipsc_models_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "TIPSC-Agent", "src", "models.py"))
if os.path.exists(_tipsc_models_path):
    _spec = importlib.util.spec_from_file_location("tipsc_models", _tipsc_models_path)
    if _spec and _spec.loader:
        _tipsc_models = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_tipsc_models)
        PreEvalOutput = getattr(_tipsc_models, "PreEvalOutput", None)
        TIPSCOutput = getattr(_tipsc_models, "TIPSCOutput", None)
        FollowUpOutput = getattr(_tipsc_models, "FollowUpOutput", None)
        EthicsOutput = getattr(_tipsc_models, "EthicsOutput", None)
        ValidationOutput = getattr(_tipsc_models, "ValidationOutput", None)
        RegulatoryOutput = getattr(_tipsc_models, "RegulatoryOutput", None)
