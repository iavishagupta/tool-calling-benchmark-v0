"""
AST decode + check utilities for the Hindi tool-calling benchmark.

decode_ast: takes the LLM's raw function-call output (a Python-call-style
string) and parses it into a structured [{func_name: {param: value}}, ...]
list using Python's ast module -- this is what BFCL does instead of regex,
since regex breaks on nested quotes/commas inside string args.

ast_checker: compares the decoded output against ground_truth
(hindi_bfcl_ground_truth_v2.json format, where each param maps to a
list of acceptable values) and returns a pass/fail + reason.
"""

import ast

def decode_ast(raw_output: str):
    """
    Parses model output like:
        get_weather_today(city="Mumbai")
    or multiple parallel calls:
        [get_weather_today(city="Mumbai"), convert_currency(amount=1000, from_currency="INR", to_currency="USD")]
    into: [{"get_weather_today": {"city": "Mumbai"}}, {"convert_currency": {...}}]
    """
    raw_output = raw_output.strip()

    # wrap a single call in a list so both forms parse the same way
    if not raw_output.startswith("["):
        raw_output = f"[{raw_output}]"

    try:
        tree = ast.parse(raw_output, mode="eval")
    except SyntaxError as e:
        return {"error": f"Could not parse model output as AST: {e}"}

    calls = tree.body.elts if isinstance(tree.body, ast.List) else [tree.body]

    parsed = []
    for call in calls:
        if not isinstance(call, ast.Call):
            return {"error": f"Expected a function call, got: {ast.dump(call)}"}

        func_name = call.func.id
        args = {}
        for kw in call.keywords:
            args[kw.arg] = _literal(kw.value)

        parsed.append({func_name: args})

    return parsed


def _literal(node):
    """Safely evaluate a single AST node into its Python value."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return ast.dump(node)  # fallback for anything non-literal


def ast_checker(model_result, ground_truth):
    """
    model_result: output of decode_ast(), e.g. [{"get_weather_today": {"city": "Mumbai"}}]
    ground_truth: list from hindi_bfcl_ground_truth_v2.json, e.g.
                  [{"get_weather_today": {"city": ["Mumbai", "मुंबई"]}}]

    Returns {"valid": bool, "error": str | None}
    """
    if isinstance(model_result, dict) and "error" in model_result:
        return {"valid": False, "error": model_result["error"]}

    # irrelevance case: no tool should be called
    if not ground_truth:
        if model_result:
            return {"valid": False, "error": "Expected no function call (irrelevant query), but got one."}
        return {"valid": True, "error": None}

    if len(model_result) != len(ground_truth):
        return {"valid": False, "error": f"Expected {len(ground_truth)} call(s), got {len(model_result)}."}

    for predicted, expected in zip(model_result, ground_truth):
        pred_func = next(iter(predicted))
        exp_func = next(iter(expected))

        if pred_func != exp_func:
            return {"valid": False, "error": f"Function mismatch: expected '{exp_func}', got '{pred_func}'."}

        pred_args = predicted[pred_func]
        exp_args = expected[exp_func]

        # every required param in ground truth must be present and match one accepted value
        for param, accepted_values in exp_args.items():
            if param not in pred_args:
                return {"valid": False, "error": f"'{pred_func}': missing required param '{param}'."}
            if pred_args[param] not in accepted_values:
                return {
                    "valid": False,
                    "error": f"'{pred_func}.{param}': got {pred_args[param]!r}, expected one of {accepted_values!r}.",
                }

        # flag unexpected extra params the model hallucinated
        extra = set(pred_args) - set(exp_args)
        if extra:
            return {"valid": False, "error": f"'{pred_func}': unexpected extra param(s) {extra}."}

    return {"valid": True, "error": None}


if __name__ == "__main__":
    # quick smoke test against hindi_4 from the ground truth file
    model_output = 'convert_currency(amount=500, from_currency="USD", to_currency="INR")'
    decoded = decode_ast(model_output)
    gt = [{"convert_currency": {"amount": [500], "from_currency": ["USD"], "to_currency": ["INR"]}}]

    print("decoded:", decoded)
    print("check:", ast_checker(decoded, gt))