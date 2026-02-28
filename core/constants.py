# Screen
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 144
SIM_RATE = 72             # Fixed simulation tick rate (Hz)
SIM_DT = 1.0 / SIM_RATE  # Seconds per simulation step

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
NEON_CYAN = (0, 255, 255)
NEON_MAGENTA = (255, 0, 255)
DESERT_ORANGE = (255, 102, 0)
SAND_YELLOW = (255, 204, 0)
SOLAR_YELLOW = (255, 255, 0)
SOLAR_WHITE = (255, 255, 200)
DARK_PANEL = (0, 0, 0, 180)
SHIELD_BLUE = (50, 150, 255)
MAGNET_PURPLE = (200, 50, 255)
SLOWMO_GREEN = (50, 255, 150)
NUKE_ORANGE = (255, 100, 50)
PHASE_CYAN = (150, 255, 255)
SURGE_PINK = (255, 50, 255)
COIN_GOLD = (255, 215, 0)
ASTEROID_GRAY = (160, 140, 120)
ASTEROID_GLOW = (200, 120, 60)

# Road geometry
ROAD_LEFT = 100
ROAD_RIGHT = SCREEN_WIDTH - 100
ROAD_WIDTH = ROAD_RIGHT - ROAD_LEFT
ROAD_CENTER = (ROAD_LEFT + ROAD_RIGHT) // 2

# Gameplay
PARTICLE_CAP = 800
GRAVITY = 0.6
MAX_LIVES = 3

# States
STATE_TITLE = "title"
STATE_PLAY = "play"
STATE_PAUSED = "paused"
STATE_GAMEOVER = "gameover"
STATE_HIGHSCORE = "highscore"
STATE_TRANSITION = "transition"
STATE_VICTORY = "victory"

# Difficulty
DIFF_EASY = "easy"
DIFF_NORMAL = "normal"
DIFF_HARD = "hard"
DIFFICULTY_SETTINGS = {
    DIFF_EASY: {
        "lives": 5, "obstacle_mult": 0.6, "spawn_div": 0.7,
        "label": "EASY", "color": SLOWMO_GREEN,
        "boss_time_mult": 1.33,       # boss arrives 33% later (4 min)
        "boss_hp_mult": 0.75,         # boss has 25% less HP
        "coin_interval": 30,          # coins more frequent
        "powerup_interval": 450,      # powerups more frequent
        "vulnerability_mult": 1.4,    # vulnerability windows 40% wider
        "boss_spawn_suppress": 0.15,  # very few obstacles during boss
    },
    DIFF_NORMAL: {
        "lives": 3, "obstacle_mult": 1.0, "spawn_div": 1.0,
        "label": "NORMAL", "color": SOLAR_YELLOW,
        "boss_time_mult": 1.0,
        "boss_hp_mult": 1.0,
        "coin_interval": 40,
        "powerup_interval": 600,
        "vulnerability_mult": 1.0,
        "boss_spawn_suppress": 0.3,
    },
    DIFF_HARD: {
        "lives": 2, "obstacle_mult": 1.5, "spawn_div": 1.4,
        "label": "HARD", "color": NEON_MAGENTA,
        "boss_time_mult": 0.67,       # boss arrives 33% sooner (2 min)
        "boss_hp_mult": 1.4,          # boss has 40% more HP
        "coin_interval": 50,          # coins less frequent
        "powerup_interval": 800,      # powerups rarer
        "vulnerability_mult": 0.7,    # vulnerability windows 30% tighter
        "boss_spawn_suppress": 0.5,   # more obstacles during boss
    },
}

# Powerup types
POWERUP_SHIELD = "shield"
POWERUP_MAGNET = "magnet"
POWERUP_SLOWMO = "slowmo"
POWERUP_NUKE = "nuke"
POWERUP_PHASE = "phase"
POWERUP_SURGE = "surge"
POWERUP_COLORS = {
    POWERUP_SHIELD: SHIELD_BLUE, POWERUP_MAGNET: MAGNET_PURPLE, POWERUP_SLOWMO: SLOWMO_GREEN,
    POWERUP_NUKE: NUKE_ORANGE, POWERUP_PHASE: PHASE_CYAN, POWERUP_SURGE: SURGE_PINK,
}
POWERUP_LABELS = {
    POWERUP_SHIELD: "S", POWERUP_MAGNET: "M", POWERUP_SLOWMO: "~",
    POWERUP_NUKE: "!", POWERUP_PHASE: "G", POWERUP_SURGE: "N",
}
POWERUP_ALL = [POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO, POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE]

# Background
ROAD_COLOR = (35, 35, 48)
ROAD_EDGE_COLOR = NEON_CYAN
ROAD_SHOULDER = (75, 45, 18)
DESERT_BG = (130, 58, 15)
DASH_LENGTH = 42
DASH_GAP = 32

# Mode indices
MODE_DESERT = 0
MODE_EXCITEBIKE = 1
MODE_MICROMACHINES = 2
MODE_NAMES = ["DESERT VELOCITY", "EXCITEBIKE", "MICRO MACHINES"]
