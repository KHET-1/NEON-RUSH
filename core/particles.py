import pygame
import random
import math

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, PARTICLE_CAP


class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color, vel=None, life=60, size=3):
        super().__init__()
        self.image = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
        col = color if len(color) == 4 else (*color[:3], 180)
        c = size + 1
        pygame.draw.circle(self.image, col, (c, c), size)
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = list(vel) if vel else [random.uniform(-2, 2), random.uniform(-1, 1)]
        self.life = self.max_life = life

    def update(self):
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.vel[0] *= 0.97
        self.vel[1] *= 0.97
        self.life -= 1
        t = self.life / self.max_life
        alpha = int(255 * (t * t))
        self.image.set_alpha(alpha)
        if self.life <= 0 or not (-80 < self.rect.x < SCREEN_WIDTH + 80 and -80 < self.rect.y < SCREEN_HEIGHT + 80):
            self.kill()


class ParticleSystem:
    def __init__(self):
        self.particles = pygame.sprite.Group()

    def emit(self, x, y, color, vel=None, life=60, size=3):
        self.particles.add(Particle(x, y, color, vel, life, size))

    def burst(self, x, y, colors, count=10, speed=5, life=40, size=3):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            c = random.choice(colors) if isinstance(colors, list) else colors
            self.particles.add(Particle(x, y, c, [vx, vy], life, size))

    def burst_directed(self, x, y, colors, count=10, speed=5, life=40, size=3,
                       angle_center=0, angle_spread=math.pi / 3):
        """Directional burst — particles within a cone around angle_center."""
        for _ in range(count):
            angle = angle_center + random.uniform(-angle_spread / 2, angle_spread / 2)
            spd = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            c = random.choice(colors) if isinstance(colors, list) else colors
            self.particles.add(Particle(x, y, c, [vx, vy], life, size))

    def update(self):
        self.particles.update()
        if len(self.particles) > PARTICLE_CAP:
            sprites = self.particles.sprites()
            for s in sprites[: len(sprites) - PARTICLE_CAP]:
                s.kill()

    def draw(self, surface):
        self.particles.draw(surface)

    def clear(self):
        for p in list(self.particles):
            p.kill()
