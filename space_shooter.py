import asyncio
import pygame
import random
import json
import math

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Shooter")

WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
RED    = (220,  50,  50)
GREEN  = (50,  220,  50)
BLUE   = (50,  100, 220)
YELLOW = (255, 220,   0)
CYAN   = (0,   220, 220)
ORANGE = (255, 140,   0)
PURPLE = (180,  50, 220)
GREY   = (180, 180, 180)

font_big   = pygame.font.SysFont("Arial", 52, bold=True)
font_med   = pygame.font.SysFont("Arial", 30, bold=True)
font_small = pygame.font.SysFont("Arial", 20)

clock = pygame.time.Clock()
FPS = 60

HIGHSCORE_FILE = "highscore.json"

def load_highscore():
    try:
        with open(HIGHSCORE_FILE) as f:
            return json.load(f).get("highscore", 0)
    except:
        return 0

def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump({"highscore": score}, f)
    except:
        pass

# --- NO AUDIO ---
def play(sfx):
    pass

# --- STARS ---
stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.5, 2.5)) for _ in range(120)]

def draw_stars():
    for x, y, s in stars:
        c = int(80 + s * 60)
        pygame.draw.circle(screen, (c, c, c), (int(x), int(y)), int(s * 0.7 + 0.5))

def scroll_stars():
    global stars
    stars = [(x, (y + s * 0.5) % HEIGHT, s) for x, y, s in stars]

# --- PARTICLES ---
particles = []

def spawn_particles(x, y, color, count=12, speed=3):
    for _ in range(count):
        angle = random.uniform(0, 6.28)
        spd   = random.uniform(1, speed)
        particles.append([x, y, spd * math.cos(angle),
                          spd * math.sin(angle),
                          color, random.randint(15, 35)])

def update_particles():
    for p in particles[:]:
        p[0] += p[2]; p[1] += p[3]; p[5] -= 1
        if p[5] <= 0:
            particles.remove(p)

def draw_particles():
    for p in particles:
        r = max(1, p[5] // 8)
        pygame.draw.circle(screen, p[4], (int(p[0]), int(p[1])), r)

# --- CLASSES ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((44, 52), pygame.SRCALPHA)
        self._draw_ship()
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 70))
        self.speed = 6
        self.health = 3
        self.max_health = 3
        self.shoot_delay = 280
        self.last_shot = 0
        self.invincible = 0
        self.triple = 0
        self.rapid  = 0
        self.shield = 0

    def _draw_ship(self):
        s = self.image
        pygame.draw.polygon(s, CYAN,   [(22, 0), (0, 52), (44, 52)])
        pygame.draw.polygon(s, BLUE,   [(22, 8), (6, 50), (38, 50)])
        pygame.draw.polygon(s, WHITE,  [(22, 14),(14, 38),(30, 38)])
        pygame.draw.rect(s,   ORANGE,  (18, 42, 8, 10))

    def update(self, keys):
        if keys[pygame.K_LEFT]  and self.rect.left > 0:        self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < WIDTH:   self.rect.x += self.speed
        if keys[pygame.K_UP]    and self.rect.top > 0:         self.rect.y -= self.speed
        if keys[pygame.K_DOWN]  and self.rect.bottom < HEIGHT: self.rect.y += self.speed
        if self.invincible > 0: self.invincible -= 1
        if self.triple  > 0:   self.triple  -= 1
        if self.rapid   > 0:   self.rapid   -= 1
        if self.shield  > 0:   self.shield  -= 1

    def shoot(self):
        now = pygame.time.get_ticks()
        delay = self.shoot_delay // 2 if self.rapid > 0 else self.shoot_delay
        if now - self.last_shot > delay:
            self.last_shot = now
            bullets = [Bullet(self.rect.centerx, self.rect.top, -12, CYAN)]
            if self.triple > 0:
                bullets.append(Bullet(self.rect.centerx, self.rect.top, -12, YELLOW, angle=-18))
                bullets.append(Bullet(self.rect.centerx, self.rect.top, -12, YELLOW, angle= 18))
            return bullets
        return []

    def take_hit(self):
        if self.shield > 0:
            spawn_particles(self.rect.centerx, self.rect.centery, (0, 180, 255), 10)
            return False
        if self.invincible > 0:
            return False
        self.health -= 1
        self.invincible = 90
        spawn_particles(self.rect.centerx, self.rect.centery, ORANGE, 16)
        return self.health <= 0

    def draw(self, surface):
        if self.invincible > 0 and (self.invincible // 6) % 2:
            return
        surface.blit(self.image, self.rect)
        if self.shield > 0:
            pygame.draw.circle(surface, (0, 180, 255), self.rect.center, 32, 2)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed, color, angle=0):
        super().__init__()
        self.image = pygame.Surface((6, 18), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, (1, 0, 4, 18), border_radius=3)
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect  = self.image.get_rect(center=(x, y))
        rad = math.radians(angle)
        self.vx = math.sin(rad) * abs(speed)
        self.vy = speed

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if self.rect.bottom < 0 or self.rect.top > HEIGHT or self.rect.right < 0 or self.rect.left > WIDTH:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    TYPES = {
        'basic':  {'color': RED,    'hp': 1, 'speed': 2,   'pts': 10,  'size': 36},
        'fast':   {'color': ORANGE, 'hp': 1, 'speed': 4,   'pts': 20,  'size': 28},
        'tank':   {'color': PURPLE, 'hp': 4, 'speed': 1.2, 'pts': 40,  'size': 46},
        'zigzag': {'color': YELLOW, 'hp': 2, 'speed': 3,   'pts': 30,  'size': 32},
    }

    def __init__(self, kind='basic'):
        super().__init__()
        t = self.TYPES[kind]
        self.kind   = kind
        self.hp     = t['hp']
        self.max_hp = t['hp']
        self.speed  = t['speed']
        self.pts    = t['pts']
        sz          = t['size']
        self.image  = pygame.Surface((sz, sz), pygame.SRCALPHA)
        self._draw(t['color'], sz)
        self.rect   = self.image.get_rect()
        self.rect.x = random.randint(0, WIDTH - sz)
        self.rect.y = -sz
        self.zdir   = 1
        self.ztimer = 0

    def _draw(self, color, sz):
        h = sz // 2
        pygame.draw.polygon(self.image, color, [(h, sz), (0, 0), (sz, 0)])
        pygame.draw.polygon(self.image, WHITE, [(h, sz-6), (4, 4), (sz-4, 4)], 2)

    def update(self):
        self.rect.y += self.speed
        if self.kind == 'zigzag':
            self.ztimer += 1
            if self.ztimer > 30:
                self.zdir  *= -1
                self.ztimer = 0
            self.rect.x += self.zdir * 3
            self.rect.x  = max(0, min(WIDTH - self.rect.width, self.rect.x))
        if self.rect.top > HEIGHT:
            self.kill()

    def hit(self):
        self.hp -= 1
        spawn_particles(self.rect.centerx, self.rect.centery,
                        self.TYPES[self.kind]['color'], 6, 2)
        if self.hp <= 0:
            spawn_particles(self.rect.centerx, self.rect.centery,
                            self.TYPES[self.kind]['color'], 20)
            return True
        return False

    def draw_health(self, surface):
        if self.max_hp > 1 and self.hp < self.max_hp:
            bw = self.rect.width
            pygame.draw.rect(surface, RED,   (self.rect.x, self.rect.y - 6, bw, 4))
            pygame.draw.rect(surface, GREEN, (self.rect.x, self.rect.y - 6,
                                              int(bw * self.hp / self.max_hp), 4))


class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx=0, vy=5):
        super().__init__()
        self.image = pygame.Surface((8, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, RED,    (0, 0, 8, 18))
        pygame.draw.ellipse(self.image, ORANGE, (2, 2, 4, 14))
        self.rect = self.image.get_rect(center=(x, y))
        self.vx, self.vy = vx, vy

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if self.rect.top > HEIGHT or self.rect.right < 0 or self.rect.left > WIDTH:
            self.kill()


class Boss(pygame.sprite.Sprite):
    def __init__(self, level):
        super().__init__()
        self.max_hp = 80 + level * 40
        self.hp     = self.max_hp
        self.level  = level
        self.image  = pygame.Surface((120, 90), pygame.SRCALPHA)
        self._draw()
        self.rect        = self.image.get_rect(center=(WIDTH // 2, -60))
        self.target_y    = 100
        self.speed       = 2
        self.dir         = 1
        self.shoot_timer = 0
        self.phase       = 1

    def _draw(self):
        s = self.image
        pygame.draw.polygon(s, PURPLE, [(60, 90), (0, 30), (120, 30)])
        pygame.draw.polygon(s, RED,    [(60, 80), (10, 35), (110, 35)])
        pygame.draw.polygon(s, WHITE,  [(60, 70), (20, 40), (100, 40)], 2)
        pygame.draw.circle(s, YELLOW,  (60, 40), 18)
        pygame.draw.circle(s, RED,     (60, 40), 10)
        pygame.draw.circle(s, WHITE,   (60, 40),  4)

    def update(self):
        if self.rect.centery < self.target_y:
            self.rect.y += self.speed + 1
        else:
            self.rect.x += self.dir * (2 + self.level * 0.5)
            if self.rect.right >= WIDTH or self.rect.left <= 0:
                self.dir *= -1
        if self.hp < self.max_hp * 0.4:
            self.phase = 2
        self.shoot_timer += 1

    def should_shoot(self):
        rate = 55 if self.phase == 1 else 35
        if self.shoot_timer >= rate:
            self.shoot_timer = 0
            return True
        return False

    def get_bullets(self):
        cx, cy = self.rect.centerx, self.rect.bottom
        bullets = [EnemyBullet(cx, cy, 0, 6)]
        if self.phase == 2:
            for a in [-25, 25]:
                rad = math.radians(a)
                bullets.append(EnemyBullet(cx, cy, math.sin(rad)*5, math.cos(rad)*5))
        return bullets

    def hit(self):
        self.hp -= 1
        spawn_particles(self.rect.centerx, self.rect.centery, PURPLE, 5, 2)
        if self.hp <= 0:
            spawn_particles(self.rect.centerx, self.rect.centery, YELLOW, 50, 6)
            return True
        return False

    def draw_health(self, surface):
        bw = 300
        bx = WIDTH // 2 - bw // 2
        by = 12
        pygame.draw.rect(surface, (60,0,0), (bx, by, bw, 18), border_radius=9)
        pygame.draw.rect(surface, RED,      (bx, by, int(bw * self.hp / self.max_hp), 18), border_radius=9)
        pygame.draw.rect(surface, WHITE,    (bx, by, bw, 18), 2, border_radius=9)
        label = font_small.render(f"BOSS  {self.hp}/{self.max_hp}", True, WHITE)
        surface.blit(label, (WIDTH // 2 - label.get_width() // 2, by + 20))


class Powerup(pygame.sprite.Sprite):
    KINDS  = ['triple', 'rapid', 'shield', 'health']
    COLORS = {'triple': YELLOW, 'rapid': CYAN, 'shield': BLUE, 'health': GREEN}
    ICONS  = {'triple': '3x',   'rapid': '>>',  'shield': 'SH', 'health': '+1'}

    def __init__(self):
        super().__init__()
        self.kind  = random.choice(self.KINDS)
        color      = self.COLORS[self.kind]
        self.image = pygame.Surface((34, 34), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (17, 17), 17)
        pygame.draw.circle(self.image, WHITE, (17, 17), 17, 2)
        txt = font_small.render(self.ICONS[self.kind], True, BLACK)
        self.image.blit(txt, (17 - txt.get_width()//2, 17 - txt.get_height()//2))
        self.rect   = self.image.get_rect()
        self.rect.x = random.randint(10, WIDTH - 44)
        self.rect.y = -40
        self.speed  = 2.5

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > HEIGHT:
            self.kill()


# --- HUD ---
def draw_hud(surface, score, highscore, health, max_health, level, player):
    for i in range(max_health):
        color = RED if i < health else (60, 0, 0)
        pygame.draw.rect(surface, color, (12 + i * 28, 12, 22, 22), border_radius=11)
        pygame.draw.rect(surface, WHITE, (12 + i * 28, 12, 22, 22), 2, border_radius=11)
    sc_txt = font_med.render(f"Score: {score}", True, WHITE)
    hs_txt = font_small.render(f"Best: {highscore}", True, GREY)
    lv_txt = font_small.render(f"Level {level}", True, CYAN)
    surface.blit(sc_txt, (WIDTH // 2 - sc_txt.get_width() // 2, 8))
    surface.blit(hs_txt, (WIDTH // 2 - hs_txt.get_width() // 2, 38))
    surface.blit(lv_txt, (WIDTH - 90, 12))
    active = []
    if player.triple > 0: active.append(("3x SHOT", YELLOW))
    if player.rapid  > 0: active.append(("RAPID",   CYAN))
    if player.shield > 0: active.append(("SHIELD",  BLUE))
    for i, (label, col) in enumerate(active):
        t = font_small.render(label, True, col)
        surface.blit(t, (WIDTH - 110, 40 + i * 22))


def draw_menu(surface, highscore):
    surface.fill(BLACK)
    draw_stars()
    title = font_big.render("SPACE SHOOTER", True, CYAN)
    sub   = font_med.render("Press SPACE or ENTER to Play", True, WHITE)
    hs    = font_med.render(f"Best Score: {highscore}", True, YELLOW)
    ctrl  = font_small.render("Arrow Keys: Move    Space: Shoot", True, GREY)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 160))
    surface.blit(sub,   (WIDTH//2 - sub.get_width()//2,   250))
    surface.blit(hs,    (WIDTH//2 - hs.get_width()//2,    300))
    surface.blit(ctrl,  (WIDTH//2 - ctrl.get_width()//2,  360))
    pygame.display.flip()


def draw_gameover(surface, score, highscore, new_best):
    surface.fill(BLACK)
    draw_stars()
    go = font_big.render("GAME OVER", True, RED)
    sc = font_med.render(f"Score: {score}", True, WHITE)
    hs = font_med.render(f"Best:  {highscore}", True, YELLOW)
    nb = font_med.render("NEW BEST!", True, GREEN) if new_best else None
    rs = font_small.render("Press SPACE or ENTER to Play Again", True, GREY)
    surface.blit(go, (WIDTH//2 - go.get_width()//2, 150))
    surface.blit(sc, (WIDTH//2 - sc.get_width()//2, 230))
    surface.blit(hs, (WIDTH//2 - hs.get_width()//2, 270))
    if nb: surface.blit(nb, (WIDTH//2 - nb.get_width()//2, 310))
    surface.blit(rs, (WIDTH//2 - rs.get_width()//2, 360))
    pygame.display.flip()


# --- MAIN LOOP ---
async def main():
    highscore = load_highscore()
    state     = "menu"

    player        = None
    all_sprites   = pygame.sprite.Group()
    bullets       = pygame.sprite.Group()
    enemies       = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()
    powerups      = pygame.sprite.Group()
    boss_group    = pygame.sprite.GroupSingle()

    score = 0; level = 1; enemy_timer = 0; boss_active = False
    boss_threshold = 500; new_best = False; enemy_spawn_rate = 90

    def reset_game():
        nonlocal player, score, level, enemy_timer, boss_active, new_best, enemy_spawn_rate
        all_sprites.empty(); bullets.empty(); enemies.empty()
        enemy_bullets.empty(); powerups.empty(); boss_group.empty()
        particles.clear()
        player = Player()
        all_sprites.add(player)
        score=0; level=1; enemy_timer=0
        boss_active=False; new_best=False; enemy_spawn_rate=90

    while True:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if state == "menu" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    reset_game(); state = "game"
                elif state == "gameover" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    reset_game(); state = "game"

        if state == "menu":
            draw_menu(screen, highscore); await asyncio.sleep(0); continue

        if state == "gameover":
            draw_gameover(screen, score, highscore, new_best); await asyncio.sleep(0); continue

        # --- GAME ---
        scroll_stars()

        if score >= level * boss_threshold and not boss_active:
            level += 1
            enemy_spawn_rate = max(30, 90 - level * 8)
            boss = Boss(level)
            boss_group.add(boss); all_sprites.add(boss)
            boss_active = True
            enemies.empty()

        if not boss_active:
            enemy_timer += 1
            if enemy_timer >= enemy_spawn_rate:
                enemy_timer = 0
                kind = random.choices(['basic','fast','tank','zigzag'], [50,20,10,20])[0]
                e = Enemy(kind)
                enemies.add(e); all_sprites.add(e)

        if random.randint(1, 600) == 1:
            p = Powerup(); powerups.add(p); all_sprites.add(p)

        if keys[pygame.K_SPACE]:
            for b in player.shoot():
                bullets.add(b); all_sprites.add(b)

        player.update(keys)
        bullets.update()
        enemies.update()
        enemy_bullets.update()
        powerups.update()
        update_particles()

        boss = boss_group.sprite
        if boss:
            boss.update()
            if boss.should_shoot():
                for eb in boss.get_bullets():
                    enemy_bullets.add(eb); all_sprites.add(eb)

        hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
        for enemy, _ in hits.items():
            if enemy.hit():
                score += enemy.pts; enemy.kill()

        if boss:
            for _ in pygame.sprite.spritecollide(boss, bullets, True):
                if boss.hit():
                    score += 300 + level * 100
                    boss.kill(); boss_active = False

        def handle_death():
            nonlocal state, highscore, new_best
            state = "gameover"
            if score > highscore:
                highscore = score; new_best = True
                save_highscore(highscore)

        for _ in pygame.sprite.spritecollide(player, enemy_bullets, True):
            if player.take_hit(): handle_death()

        for _ in pygame.sprite.spritecollide(player, enemies, True):
            if player.take_hit(): handle_death()

        for pu in pygame.sprite.spritecollide(player, powerups, True):
            if pu.kind == 'triple': player.triple = 300
            if pu.kind == 'rapid':  player.rapid  = 300
            if pu.kind == 'shield': player.shield = 300
            if pu.kind == 'health' and player.health < player.max_health:
                player.health += 1
            spawn_particles(pu.rect.centerx, pu.rect.centery, Powerup.COLORS[pu.kind], 15)

        # --- DRAW ---
        screen.fill((5, 5, 18))
        draw_stars()
        draw_particles()

        for e in enemies:
            screen.blit(e.image, e.rect)
            e.draw_health(screen)

        if boss:
            screen.blit(boss.image, boss.rect)
            boss.draw_health(screen)

        enemy_bullets.draw(screen)
        powerups.draw(screen)
        bullets.draw(screen)
        player.draw(screen)

        draw_hud(screen, score, highscore, player.health, player.max_health, level, player)

        pygame.display.flip()
        await asyncio.sleep(0)

asyncio.run(main())
