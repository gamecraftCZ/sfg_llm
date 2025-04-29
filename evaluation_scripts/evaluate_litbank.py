import argparse
import json
import os
from pathlib import Path
from typing import Any
from tqdm import tqdm

from components import LoadLitbankBookGroundtruthComponent, LLMQuotationAttributorComponent, \
    SavePipelineDataComponentToJson, QuotationExtractionEvaluationComponent, ComponentParser
from pipeline import Pipeline
from sfg_types import TextPartType


def process_book(book: str, litbank_repo_path: Path, attributor_params: dict[str, Any], pipeline_save_file: Path) -> dict[str, Any]:
    os.makedirs(Path(pipeline_save_file).parent, exist_ok=True)
    components = [
        LoadLitbankBookGroundtruthComponent(params={"repo": str(litbank_repo_path), "book_id": str(book), "use_gt_text": "true", "use_gt_characters": "true"}),
        LLMQuotationAttributorComponent(params=attributor_params),
        QuotationExtractionEvaluationComponent(params={}),
        # Save the pipeline data to a JSON file
        SavePipelineDataComponentToJson(params={"file": str(pipeline_save_file)}),
    ]
    pipeline = Pipeline(components)
    data = pipeline.setup_and_run()
    stats = {
        "pipeline_file": data.additional_attributes["last_save_path"],
        "quotation_iou_score": data.additional_attributes["quotation_iou_score"],
        "relative_text_parts_to_gt_edit_distance": data.additional_attributes["relative_text_parts_to_gt_edit_distance"],
        "matched_quotes_accuracy": data.additional_attributes["gt_matched_quotes_accuracy"],
        "llm_total_input_tokens": data.additional_attributes["llm_quotation_attribution_stats"]["llm_total_input_tokens"],
        "llm_total_output_tokens": data.additional_attributes["llm_quotation_attribution_stats"]["llm_total_output_tokens"],
        "pred_total_text_parts": len(data.text_as_parts),
        "pred_other_text_parts": len([d for d in data.text_as_parts if d.type == TextPartType.OTHER]),
        "pred_quote_text_parts": len([d for d in data.text_as_parts if d.type == TextPartType.QUOTE]),
        "gt_total_text_parts": len(data.additional_attributes["text_as_parts_gt"]),
        "gt_other_text_parts": len([d for d in data.additional_attributes["text_as_parts_gt"] if d.type == TextPartType.OTHER]),
        "gt_quote_text_parts": len([d for d in data.additional_attributes["text_as_parts_gt"] if d.type == TextPartType.QUOTE]),
    }
    return stats


def main():
    parser = argparse.ArgumentParser(description="Evaluate component against quotation attribution on Litbank dataset.")
    parser.add_argument(
        "--litbank_repo_path",
        type=Path,
        required=True,
        help="Path to the Litbank repository.",
    )
    parser.add_argument(
        "--book",
        type=str,
        required=False,
        action="append",
    )
    parser.add_argument(
        "--all_books",
        required=False,
        action="store_true",
        help="Process all books in the Litbank repository.",
    )
    parser.add_argument(
        "--out_stats_file_prefix",
        type=str,
        default="stats_litbank",
    )
    parser.add_argument(
        "--attributor_params",
        type=str,
        required=True,
        help="LLMQuotationAttributorComponent params",
    )
    args = parser.parse_args()

    if not args.book and not args.all_books:
        parser.error("Either --book or --all_books must be specified.")

    # Check if litbank_repo_path exists
    if not args.litbank_repo_path.exists():
        raise ValueError(f"Litbank repository path {args.litbank_repo_path} does not exist.")

    # Load list of books
    all_books = LoadLitbankBookGroundtruthComponent.list_litbank_books(args.litbank_repo_path)
    if args.all_books:
        books = all_books
        print(f"Processing all books in the Litbank repository. All books: {all_books}")
    else:
        books = args.book if args.book else []
        # Check if specified books exist
        for book in books:
            if book not in all_books:
                raise ValueError(f"Book {book} not found in Litbank repository. Available books: {all_books}")

    # Load attributor params
    attributor_params = ComponentParser.parse_component_params(args.attributor_params)
    print(f"Parsed attributor_params: {attributor_params}")

    # Process book by book
    stats = {}
    for book in tqdm(books, desc="Processing books", unit="book"):
        pipeline_save_file = Path(f"output/attributions_litbank_book_{book}_%Y-%m-%d_%H-%M-%S.json")
        try:
            stat = process_book(book, args.litbank_repo_path, attributor_params, pipeline_save_file)
            stat["attributor_params"] = args.attributor_params
            stats[book] = stat
        except Exception as e:
            print("Exception while processing book:", book, e)
            print("Skipping book because of exception above:", book)

    print("All books processed")
    print(f"Stats: {stats}")

    # Save stats to file
    out_stats_file = Path(f"{args.out_stats_file_prefix}_{'-'.join(books) if len(books) < 5 else f'num_books_{len(books)}'}.json")
    os.makedirs(out_stats_file.parent, exist_ok=True)
    with open(out_stats_file, "w+") as f:
        json.dump(stats, f, indent=2)

    print(f"Stats saved to {out_stats_file}")
    print("[DONE]")


if __name__ == "__main__":
    main()
