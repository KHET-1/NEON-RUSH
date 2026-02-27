import random


class ScreenShake:
    def __init__(self):
        self.intensity = 0
        self.duration = 0
        self.offset_x = 0
        self.offset_y = 0

    def trigger(self, intensity, duration):
        self.intensity = intensity
        self.duration = duration

    def update(self):
        if self.duration > 0:
            self.offset_x = random.randint(-int(self.intensity), int(self.intensity))
            self.offset_y = random.randint(-int(self.intensity), int(self.intensity))
            self.duration -= 1
            self.intensity = max(1, self.intensity - 0.3)
        else:
            self.offset_x = 0
            self.offset_y = 0

    def get_offset(self):
        return (int(self.offset_x), int(self.offset_y))
