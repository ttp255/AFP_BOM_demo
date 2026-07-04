from app.services.llm_bom_service import (
    _clean_explanation_text,
    _consultant_prompt,
    clean_catalog_language,
    describe_feature_outcomes,
)


def test_catalog_labels_are_translated_before_prompting() -> None:
    source = (
        "Hiệu quả vì exterior wall paint phù hợp với khu vực exterior wall. "
        "Dữ liệu sản phẩm cho biết: chống UV và chống thấm."
    )
    cleaned = clean_catalog_language(source)
    assert "exterior" not in cleaned.casefold()
    assert "Hiệu quả vì" not in cleaned
    assert "Dữ liệu sản phẩm cho biết" not in cleaned
    assert "sơn dùng cho tường ngoài trời" in cleaned
    assert "tường ngoài trời" in cleaned


def test_llm_output_cleanup_removes_standalone_english_labels() -> None:
    cleaned = _clean_explanation_text(
        "Exterior paint phù hợp cho exterior wall vì có khả năng chống UV."
    )
    assert "exterior" not in cleaned.casefold()
    assert cleaned == (
        "Sơn ngoài trời phù hợp cho tường ngoài trời vì có khả năng chống UV"
    )

def test_feature_tags_are_converted_to_practical_outcomes() -> None:
    outcomes = describe_feature_outcomes(
        ["uv_resistant", "water_resistant", "color_retention"]
    )
    assert outcomes == [
        "giảm tác động của tia UV lên màng sơn, giúp màu sắc bền hơn khi phơi nắng",
        "hạn chế nước thấm qua bề mặt, giúp tường ít bị xuống cấp do ẩm",
        "duy trì màu sắc ổn định lâu hơn, giảm nhu cầu sơn lại sớm",
    ]
    assert not any("_" in outcome for outcome in outcomes)


def test_prompt_requires_function_and_outcome_not_catalog_fit() -> None:
    prompt = _consultant_prompt({}, [])
    assert "Never justify effectiveness merely" in prompt
    assert "what it protects or improves" in prompt
    assert "cause-and-effect statement" in prompt