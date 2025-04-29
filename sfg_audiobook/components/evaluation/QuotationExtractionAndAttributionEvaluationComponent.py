import Levenshtein
import numpy as np

from common.utils import merge_neighbouring_text_parts_of_the_same_type_and_character, array_to_ranges, \
    remove_duplicate_spaces
from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData, TextPart
from structure.AbstractComponent import AbstractComponent


class QuotationExtractionEvaluationComponent(AbstractComponent):
    """
    Evaluates the extracted quotations text_parts in the text with additional_attributes["text_parts_gt"].
    """

    @staticmethod
    def get_help() -> str:
        return """Evaluates the extracted quotations text_parts in the text with loaded ground truth quotations."""

    def setup(self, data: PipelineData):
        pass

    @staticmethod
    def _text_parts_to_text_and_mask(text_parts: list[TextPart]) -> tuple[str, np.ndarray, np.ndarray]:
        full_text = "".join([part.text for part in text_parts])
        quotes_mask = np.zeros(len(full_text), dtype=int)  # Quote id for each character in predicted text.
        text_parts_ids = np.zeros(len(full_text), dtype=int)  # Text part id for each text part in predicted text.

        start = 0
        for part in text_parts:
            if part.type == "quote":
                quotes_mask[start:start + len(part.text)] = part.id
            text_parts_ids[start:start + len(part.text)] = part.id
            start += len(part.text)

        return full_text, quotes_mask, text_parts_ids

    def run(self, data: PipelineData):
        predicted_text_parts = data.text_as_parts
        gt_text_parts = [TextPart.model_validate(d) for d in data.additional_attributes["text_as_parts_gt"]]

        # Handle edge cases
        if not predicted_text_parts and not gt_text_parts:
            data.additional_attributes["iou_quotation_score"] = 1.0
            data.additional_attributes["iou_quotation_scores"] = []
            return

        if not predicted_text_parts or not gt_text_parts:
            data.additional_attributes["iou_quotation_score"] = 0.0
            data.additional_attributes["iou_quotation_scores"] = []
            return

        # Remove blank spaces and remove empty text parts
        gt_text_parts = remove_duplicate_spaces([part.model_copy() for part in gt_text_parts if part.text.strip() + " "], strip=True)
        predicted_text_parts = remove_duplicate_spaces([part.model_copy() for part in predicted_text_parts if part.text.strip() + " "], strip=True)

        # Preprocess text parts
        gt_text_parts_merged = merge_neighbouring_text_parts_of_the_same_type_and_character(gt_text_parts)
        predicted_text_parts_merged = merge_neighbouring_text_parts_of_the_same_type_and_character(predicted_text_parts)

        # Calculations
        gt_text_full, gt_quotes_mask, gt_text_parts_ids = QuotationExtractionEvaluationComponent._text_parts_to_text_and_mask(gt_text_parts_merged)
        pred_text_full, pred_quotes_mask, pred_text_parts_ids = QuotationExtractionEvaluationComponent._text_parts_to_text_and_mask(predicted_text_parts_merged)

        # Get the edit distance operations (edit script)
        ops = Levenshtein.editops(pred_text_full, gt_text_full)
        edit_distance = len(ops)
        relative_edit_distance = edit_distance / max(len(pred_text_full), len(gt_text_full))

        print(f"Relative edit distance ({edit_distance} / {max(len(pred_text_full), len(gt_text_full))}): {relative_edit_distance:4f}")
        data.additional_attributes["relative_text_parts_to_gt_edit_distance"] = relative_edit_distance


        # TODO optimize to not copy the array for each delete or insert that is done in the ops is done.
        # Use the edit ops to extend the pred_quotes_mask to the whole text.
        pred_quotes_mask_extended = np.copy(pred_quotes_mask)
        pred_text_parts_ids_extended = np.copy(pred_text_parts_ids)
        for op in reversed(ops):
            action, pos1, pos2 = op
            if action == 'delete':
                pred_quotes_mask_extended = np.delete(pred_quotes_mask_extended, pos1)
                pred_text_parts_ids_extended = np.delete(pred_text_parts_ids_extended, pos1)
            elif action == 'insert':
                pred_quotes_mask_extended = np.insert(pred_quotes_mask_extended, pos1, 0)
                pred_text_parts_ids_extended = np.insert(pred_text_parts_ids_extended, pos1, 0)
            elif action == 'replace':
                pass

        # Calculate IoU
        gt_mask = gt_quotes_mask.astype(bool)
        pred_mask = pred_quotes_mask_extended.astype(bool)

        intersection = np.logical_and(gt_mask, pred_mask)
        union = np.logical_or(gt_mask, pred_mask)
        iou_score = np.sum(intersection) / np.sum(union) if np.sum(union) > 0 else 0.0

        # Errors
        mistakes = np.logical_xor(gt_mask, pred_mask)
        mistakes_locs = np.where(mistakes)[0]
        mistakes_locs_ranges = array_to_ranges(mistakes_locs)
        print(f"Quotation Mistakes ({len(mistakes_locs_ranges)}):")
        for mistake_range in mistakes_locs_ranges:
            pred_quotes_in_range_ids = pred_text_parts_ids_extended[mistake_range[0]:mistake_range[1]]
            gt_quotes_in_range_ids = gt_text_parts_ids[mistake_range[0]:mistake_range[1]]

            pred_quotes_in_range = [part for part in predicted_text_parts_merged if part.id in pred_quotes_in_range_ids]
            gt_quotes_in_range = [part for part in gt_text_parts_merged if part.id in gt_quotes_in_range_ids]

            print(f"  {mistake_range[0]}-{mistake_range[1]}: '{gt_text_full[mistake_range[0]:mistake_range[1]]}'")
            print(f"    Predicted: {pred_quotes_in_range}")
            print(f"    GT: {gt_quotes_in_range}")


        print(f"Total Quotation IoU score: {iou_score:.4f}")
        data.additional_attributes["quotation_iou_score"] = iou_score

        # Match predicted quotes with their gt counterparts and calculate accuracy
        pred_quote_attribution_stats = []
        for quote in predicted_text_parts_merged:
            if quote.type == "quote":
                quote_mask = pred_quotes_mask_extended == quote.id
                quote_gt_matched_mask = gt_quotes_mask * quote_mask
                quote_gt_matched_ids = np.unique(quote_gt_matched_mask)

                if len(quote_gt_matched_ids) == 0:
                    pred_quote_attribution_stats.append({
                        "pred_quote": quote,
                        "gt_quote": None,
                        "correct": False,
                    })

                for matched_gt_quote_id in quote_gt_matched_ids:
                    if matched_gt_quote_id == 0: continue
                    matched_gt_quote = next((part for part in gt_text_parts_merged if part.id == matched_gt_quote_id), None)
                    if matched_gt_quote:
                        pred_quote_attribution_stats.append({
                            "pred_quote": quote,
                            "gt_quote": matched_gt_quote,
                            "correct": quote.character_identifier == matched_gt_quote.character_identifier,
                        })
                    else:
                        raise ValueError(f"GT quote with id {matched_gt_quote_id} not found in gt_text_parts_merged, but should!")

        correct = sum(1 for stat in pred_quote_attribution_stats if stat["correct"])
        total = len(pred_quote_attribution_stats)
        accuracy = correct / total if total > 0 else 0.0
        print(f"Matched quotes accuracy ({correct}/{total}): {accuracy:.4f}")
        data.additional_attributes["matched_quotes_accuracy"] = accuracy

        # Match gt quotes with their pred counterparts and calculate accuracy
        gt_quote_attribution_stats = []
        for quote in gt_text_parts_merged:
            if quote.type == "quote":
                quote_mask = gt_quotes_mask == quote.id
                quote_pred_matched_mask = pred_quotes_mask_extended * quote_mask
                quote_pred_matched_ids = np.unique(quote_pred_matched_mask)

                if len(quote_pred_matched_ids) == 0:
                    gt_quote_attribution_stats.append({
                        "gt_quote": quote,
                        "pred_quote": None,
                        "correct": False,
                    })

                for matched_pred_quote_id in quote_pred_matched_ids:
                    if matched_pred_quote_id == 0: continue
                    matched_pred_quote = next((part for part in predicted_text_parts_merged if part.id == matched_pred_quote_id), None)
                    if matched_pred_quote:
                        gt_quote_attribution_stats.append({
                            "gt_quote": quote,
                            "pred_quote": matched_pred_quote,
                            "correct": quote.character_identifier == matched_pred_quote.character_identifier,
                        })
                    else:
                        raise ValueError(f"Pred quote with id {matched_pred_quote_id} not found in pred_text_parts_merged, but should!")

        correct = sum(1 for stat in gt_quote_attribution_stats if stat["correct"])
        total = len(gt_quote_attribution_stats)
        accuracy = correct / total if total > 0 else 0.0
        print(f"GT to pred matched quotes accuracy ({correct}/{total}): {accuracy:.4f}")
        data.additional_attributes["gt_matched_quotes_accuracy"] = accuracy


ComponentsRegister.register_component("evaluation_quotation_extraction", QuotationExtractionEvaluationComponent)
