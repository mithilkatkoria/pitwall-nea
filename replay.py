"""Shared race clock and deterministic lap progress."""
from bisect import bisect_right
from dataclasses import dataclass
from model import number_in_range


@dataclass
class Replay:
    duration: float = 0.0
    elapsed: float = 0.0
    speed: int = 120
    playing: bool = False

    def advance(self, seconds):
        number_in_range(seconds, "Frame seconds", 0, 60)
        if self.playing:
            self.elapsed = min(self.duration, self.elapsed+seconds*self.speed)
            if self.elapsed >= self.duration: self.playing = False

    def toggle(self):
        if self.duration <= 0: return
        if self.elapsed >= self.duration: self.elapsed = 0.0
        self.playing = not self.playing

    def restart(self):
        self.elapsed = 0.0
        self.playing = False

    def scrub(self, fraction):
        number_in_range(fraction, "Timeline fraction", -1000, 1000)
        self.elapsed = max(0,min(1,fraction))*self.duration
        self.playing = False

    def cycle_speed(self):
        speeds = (60,120,300)
        self.speed = speeds[(speeds.index(self.speed)+1)%len(speeds)]


def progress(result, elapsed):
    number_in_range(elapsed,"Replay seconds",0,1e9)
    if elapsed >= result.total: return float(len(result.laps)), len(result.laps)-1
    index = bisect_right([lap.elapsed for lap in result.laps],elapsed)
    start = result.laps[index-1].elapsed if index else 0
    fraction = (elapsed-start)/result.laps[index].time
    return index+fraction,index
