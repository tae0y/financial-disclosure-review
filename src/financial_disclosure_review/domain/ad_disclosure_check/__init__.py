"""Judging the ad page against the mandatory ad disclosures."""

from .check import judge_disclosure, judge_original

__all__ = ["judge_disclosure", "judge_original"]
