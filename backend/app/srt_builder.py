from dataclasses import dataclass
from typing import List
import srt
from datetime import timedelta

@dataclass
class Cue:
    index: int
    start_ms: int
    end_ms: int
    text: str

def ms_to_td(ms: int) -> timedelta:
    return timedelta(milliseconds=int(ms))

def clamp_non_overlapping(cues: List[Cue], min_gap_ms: int = 1) -> List[Cue]:
    out = []
    last_end = -1
    for c in cues:
        start = max(c.start_ms, last_end + min_gap_ms)
        end = max(c.end_ms, start + min_gap_ms)
        out.append(Cue(c.index, start, end, c.text))
        last_end = end
    return out

def build_srt(cues: List[Cue]) -> str:
    subs = []
    for c in cues:
        subs.append(srt.Subtitle(
            index=c.index,
            start=ms_to_td(c.start_ms),
            end=ms_to_td(c.end_ms),
            content=(c.text or "").strip()
        ))
    return srt.compose(subs)
