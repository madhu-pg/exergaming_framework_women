# launcher_all_pages.py

import pygame, sys, os
import json
import importlib.util
from pygame.locals import *
from path_utils import get_app_root, get_data_dir

pygame.init()
pygame.font.init()

# ============== CONFIG ==============
info = pygame.display.Info()
SCREEN_SIZE = (info.current_w, info.current_h)   # fullscreen resolution
FPS = 30
TITLE = "Exercise Launcher"

# Automatic font scaling for small screens:
# reference width where fonts are "normal"
REF_WIDTH = 1280
scale_factor = max(0.7, min(1.0, SCREEN_SIZE[0] / REF_WIDTH))  # clamp between 0.7 and 1.0

# Fonts (scaled)
BASE_FONT = pygame.font.SysFont("arial", int(20 * scale_factor))
BTN_FONT = pygame.font.SysFont("arial", int(26 * scale_factor), bold=True)
HEADER_FONT = pygame.font.SysFont("arial", int(42 * scale_factor), bold=True)
FORM_TITLE_FONT = pygame.font.SysFont("arial", int(28 * scale_factor), bold=True)
LABEL_FONT = pygame.font.SysFont("arial", int(18 * scale_factor))

# Place your 17 background images here (order = page numbers 1..17)
BASE_DIR = get_app_root()
IMAGE_FILES = [os.path.join(BASE_DIR, "images", f"img{i}.png") for i in range(1, 18)]

# Map the exercise choices to (benefit_page, instruction_page, game_folder)
exercise_map = {
    "sed_cardio_step_touch_easy":   {"benefit": 6,  "instruction": 12, "game_folder": "game_folder1/cardio"},
    "sed_cardio_step_touch_med":    {"benefit": 6,  "instruction": 12, "game_folder": "game_folder1/cardiomed"},
    "sed_cardio_step_touch_hard":   {"benefit": 6,  "instruction": 12, "game_folder": "game_folder1/cardiodif"},
    "sed_strength_side_leg_easy":   {"benefit": 7,  "instruction": 13, "game_folder": "game_folder2/stretch"},
    "sed_strength_side_leg_med":    {"benefit": 7,  "instruction": 13, "game_folder": "game_folder2/stretchmed"},
    "sed_strength_side_leg_hard":   {"benefit": 7,  "instruction": 13, "game_folder": "game_folder2/stretchdif"},
    "sed_stretch_side_stretch_easy":{"benefit": 8,  "instruction": 14, "game_folder": "game_folder3/bent"},
    "sed_stretch_side_stretch_med": {"benefit": 8,  "instruction": 14, "game_folder": "game_folder3/bentmed"},
    "sed_stretch_side_stretch_hard":{"benefit": 8,  "instruction": 14, "game_folder": "game_folder3/bentdif"},
    "pcod_cardio_low_march_easy":   {"benefit": 9,  "instruction": 15, "game_folder": "game_folder4/March"},
    "pcod_cardio_low_march_med":    {"benefit": 9,  "instruction": 15, "game_folder": "game_folder4/Marchmed"},
    "pcod_cardio_low_march_hard":   {"benefit": 9,  "instruction": 15, "game_folder": "game_folder4/Marchdif"},
    "pcod_strength_squats_easy":    {"benefit": 10, "instruction": 16, "game_folder": "game_folder5/squat"},
    "pcod_strength_squats_med":     {"benefit": 10, "instruction": 16, "game_folder": "game_folder5/squatmed"},
    "pcod_strength_squats_hard":    {"benefit": 10, "instruction": 16, "game_folder": "game_folder5/squatdif"},
    "pcod_stretch_spinal_twist_easy": {"benefit":11, "instruction":17, "game_folder": "game_folder6/twist"},
    "pcod_stretch_spinal_twist_med":  {"benefit":11, "instruction":17, "game_folder": "game_folder6/twistmed"},
    "pcod_stretch_spinal_twist_hard": {"benefit":11, "instruction":17, "game_folder": "game_folder6/twistdif"},
}

# If your games' main script has a different name, map it here:




# ============== UTILS: Button & Input Box ==============
class Button:
    def __init__(self, rect, text, font=BTN_FONT, bg=(240,240,240), fg=(0,0,0),
                 border_color=(0,0,0), border_width=3, radius=10):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg
        self.border_color = border_color
        self.border_width = border_width
        self.radius = radius

    def draw(self, surf, highlight=False, highlight_color=(0,150,0)):
        # background
        bg = self.bg
        pygame.draw.rect(surf, bg, self.rect, border_radius=self.radius)
        # border: if highlight True, draw highlight border
        if highlight:
            pygame.draw.rect(surf, highlight_color, self.rect, self.border_width + 2, border_radius=self.radius)
        else:
            pygame.draw.rect(surf, self.border_color, self.rect, self.border_width, border_radius=self.radius)
        txt = self.font.render(self.text, True, self.fg)
        txt_rect = txt.get_rect(center=self.rect.center)
        surf.blit(txt, txt_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class InputBox:
    def __init__(self, rect, placeholder="", font=BASE_FONT):
        self.rect = pygame.Rect(rect)
        self.text = ""
        self.placeholder = placeholder
        self.font = font
        self.active = False
        self.cursor_timer = 0

    def handle_event(self, event):
        if event.type == MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == KEYDOWN and self.active:
            if event.key == K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == K_RETURN:
                self.active = False
            else:
                if len(self.text) < 60:
                    self.text += event.unicode

    def draw(self, surf):
        pygame.draw.rect(surf, (255,255,255), self.rect, border_radius=6)
        pygame.draw.rect(surf, (0,0,0), self.rect, 2, border_radius=6)  # stronger border
        if self.text != "":
            txt = self.font.render(self.text, True, (0,0,0))
        else:
            txt = self.font.render(self.placeholder, True, (120,120,120))
        surf.blit(txt, (self.rect.x + 12, self.rect.y + (self.rect.height - txt.get_height())//2))
        # cursor
        if self.active:
            self.cursor_timer = (self.cursor_timer + 1) % 60
            if self.cursor_timer < 30:
                cursor_x = self.rect.x + 12 + (self.font.size(self.text)[0] if self.text else 0)
                pygame.draw.line(surf, (0,0,0), (cursor_x, self.rect.y+8), (cursor_x, self.rect.y + self.rect.height - 8), 2)

# ============== LOAD IMAGES ==============
def load_images(paths, size):
    imgs = {}
    for i, p in enumerate(paths, start=1):
        if not os.path.exists(p):
            print(f"[WARN] Image not found: {p}  (placeholder used).")
            surf = pygame.Surface(size)
            surf.fill((200,200,200))
            label = BASE_FONT.render(f"Missing: {p}", True, (100,0,0))
            surf.blit(label, (20,20))
            imgs[i] = surf
            continue
        img = pygame.image.load(p).convert_alpha()
        img = pygame.transform.smoothscale(img, size)
        imgs[i] = img
    return imgs

# ============== LAUNCH GAME ==============
def load_game_module(game_folder):
    """Dynamically load game module from folder - works in frozen and unfrozen mode"""
    # In frozen mode, we need to add the parent directory to sys.path
    # so Python can find the game modules as packages
    app_root = get_app_root()
    print(f"[DEBUG load_game_module] App root: {app_root}")
    print(f"[DEBUG load_game_module] sys.frozen: {getattr(sys, 'frozen', False)}")

    if app_root not in sys.path:
        sys.path.insert(0, app_root)
        print(f"[DEBUG load_game_module] Added {app_root} to sys.path")

    # Convert folder path to module path (e.g., "game_folder1/cardio" -> "game_folder1.cardio")
    module_path = game_folder.replace('/', '.').replace('\\', '.')
    print(f"[DEBUG load_game_module] Module path: {module_path}")

    # Try to import the game module
    try:
        # Try common module names in order
        game_module_names = [
            'cardiogame', 'cardiogame1', 'cardiogame2',
            'stretchgame', 'stretchgame1', 'stretchgame2',
            'bending', 'bending1', 'bending2',
            'marchinggame', 'marchinggame1', 'marchinggame2',
            'squatgame', 'squatgame1', 'squatgame2',
            'tiltgame'
        ]

        for game_name in game_module_names:
            try:
                full_module_name = f"{module_path}.{game_name}"
                print(f"[DEBUG load_game_module] Trying to import: {full_module_name}")
                module = __import__(full_module_name, fromlist=['run_game'])
                if hasattr(module, 'run_game'):
                    print(f"[DEBUG load_game_module] Successfully loaded: {full_module_name}")
                    return module
                else:
                    print(f"[DEBUG load_game_module] Module {full_module_name} has no run_game function")
            except (ImportError, AttributeError) as e:
                print(f"[DEBUG load_game_module] Failed to import {full_module_name}: {e}")
                continue

        raise ImportError(f"Could not find a valid game module in {game_folder}")
    except Exception as e:
        print(f"[ERROR] Failed to load game from {game_folder}: {e}")
        import traceback
        traceback.print_exc()
        raise

# ============== MAIN UI FLOW ==============
def main():
    screen = pygame.display.set_mode(SCREEN_SIZE, pygame.FULLSCREEN)
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    # load images
    images = load_images(IMAGE_FILES, SCREEN_SIZE)

    # --- Page 1: Start button moved slightly upward, larger, with border
    start_btn = Button(
        rect=(SCREEN_SIZE[0]//2 - int(120 * scale_factor), SCREEN_SIZE[1] - int(220 * scale_factor),
              int(240 * scale_factor), int(70 * scale_factor)),
        text="Start",
        font=pygame.font.SysFont("arial", int(32 * scale_factor), bold=True),
        bg=(255,255,255),
        border_color=(0,0,0),
        border_width=4,
        radius=12
    )

    # --- Page 2: form (centered) we'll compute positions dynamically
       # Increased form height and spacing to avoid overlapping inputs
    form_width = int(590 * scale_factor)
    form_height = int(490 * scale_factor)   # increased more for extra vertical space
    form_x = (SCREEN_SIZE[0] - form_width)//2
    form_y = (SCREEN_SIZE[1] - form_height)//2

    input_h = int(60 * scale_factor)        # taller input boxes
    input_w = form_width - int(80 * scale_factor)
    spacing = int(30 * scale_factor)        # bigger spacing between inputs

    input_name = InputBox(
        rect=(form_x + int(40*scale_factor), form_y + int(70*scale_factor), input_w, input_h),
        placeholder="Enter full name"
    )
    input_age  = InputBox(
        rect=(form_x + int(40*scale_factor), input_name.rect.y + input_h + spacing, input_w, input_h),
        placeholder="Age"
    )
    input_height = InputBox(
        rect=(form_x + int(40*scale_factor), input_age.rect.y + input_h + spacing, input_w, input_h),
        placeholder="Height (cm)"
    )
    input_weight = InputBox(
        rect=(form_x + int(40*scale_factor), input_height.rect.y + input_h + spacing, input_w, input_h),
        placeholder="Weight (kg)"
    )

    btn_y = input_weight.rect.y + input_h + int(30 * scale_factor)
    form_next_btn = Button(rect=(form_x + form_width//2 + int(10*scale_factor), btn_y, int(140*scale_factor), int(48*scale_factor)), text="Next")
    form_back_btn = Button(rect=(form_x + form_width//2 - int(150*scale_factor), btn_y, int(140*scale_factor), int(48*scale_factor)), text="Back")

    # Page 3: choices - wider buttons
    sed_btn = Button(rect=(int(60*scale_factor), int(220*scale_factor), int(420*scale_factor), int(56*scale_factor)), text="Sedentary lifestyle - Weight Management")
    pcod_btn = Button(rect=(SCREEN_SIZE[0]-int(60*scale_factor)-int(420*scale_factor), int(220*scale_factor), int(420*scale_factor), int(56*scale_factor)), text="PCOD/PCOS specific exercise")

    # Page 4 (sedentary menu): three vertically stacked buttons
    sed_cardio_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(200*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Cardio: Step touch with arm swings")
    sed_strength_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(270*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Strength: Standing Side leg raises")
    sed_stretch_btn  = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(340*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Stretching: Standing Side Stretch")

    # Page 5 (pcod menu)
    pcod_cardio_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(200*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Cardio: Low-impact marching")
    pcod_strength_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(270*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Strength/Resistance: Squats")
    pcod_stretch_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(340*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Stretch: Gentle spinal twist")

    # Difficulty selection buttons (new pages 18-27)
    easy_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(200*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Easy")
    med_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(270*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Medium")
    hard_btn = Button(rect=(SCREEN_SIZE[0]//2 - int(250*scale_factor), int(340*scale_factor), int(500*scale_factor), int(56*scale_factor)), text="Hard")

    # Next and Back buttons (reused across many pages)
    bottom_next_btn = Button(rect=(SCREEN_SIZE[0]-int(180*scale_factor), SCREEN_SIZE[1]-int(90*scale_factor), int(160*scale_factor), int(56*scale_factor)), text="Next")
    bottom_back_btn = Button(rect=(20, SCREEN_SIZE[1]-int(90*scale_factor), int(160*scale_factor), int(56*scale_factor)), text="Back")

    # state:
    page = 1   # current page number
    running = True
    selected_exercise_key = None
    last_selected_exercise = None  # for persistent highlight when revisiting menus
    last_exercise_base = None  # track base exercise for difficulty pages
    user_data = {"name":"","age":"","height":"","weight":""}

    # map exercise base names to their buttons for highlighting
    exercise_buttons = {
        "sed_cardio_step_touch": sed_cardio_btn,
        "sed_strength_side_leg": sed_strength_btn,
        "sed_stretch_side_stretch": sed_stretch_btn,
        "pcod_cardio_low_march": pcod_cardio_btn,
        "pcod_strength_squats": pcod_strength_btn,
        "pcod_stretch_spinal_twist": pcod_stretch_btn,
    }

    # map of pages -> back targets
    back_page_map = {
        2: 1,   # page2 back -> page1
        4: 3, 3: 2,
        5: 3,
        # Difficulty pages back to exercise pages
        18: 4, 19: 4, 20: 4,  # sed cardio difficulty back to page 4
        21: 4, 22: 4, 23: 4,  # sed strength difficulty back to page 4
        24: 4, 25: 4, 26: 4,  # sed stretch difficulty back to page 4
        27: 5, 28: 5, 29: 5,  # pcod cardio difficulty back to page 5
        30: 5, 31: 5, 32: 5,  # pcod strength difficulty back to page 5
        33: 5, 34: 5, 35: 5,  # pcod stretch difficulty back to page 5
        # Benefit pages back to difficulty pages (we'll handle dynamically)
        6: None, 7: None, 8: None, 9: None, 10: None, 11: None,
        # Instruction pages back to benefit pages
        12: 6, 13: 7, 14: 8, 15: 9, 16: 10, 17: 11,
    }

    # Difficulty page mapping (page -> (exercise_base, difficulty))
    difficulty_pages = {
        18: ("sed_cardio_step_touch", "easy"),
        19: ("sed_cardio_step_touch", "med"),
        20: ("sed_cardio_step_touch", "hard"),
        21: ("sed_strength_side_leg", "easy"),
        22: ("sed_strength_side_leg", "med"),
        23: ("sed_strength_side_leg", "hard"),
        24: ("sed_stretch_side_stretch", "easy"),
        25: ("sed_stretch_side_stretch", "med"),
        26: ("sed_stretch_side_stretch", "hard"),
        27: ("pcod_cardio_low_march", "easy"),
        28: ("pcod_cardio_low_march", "med"),
        29: ("pcod_cardio_low_march", "hard"),
        30: ("pcod_strength_squats", "easy"),
        31: ("pcod_strength_squats", "med"),
        32: ("pcod_strength_squats", "hard"),
        33: ("pcod_stretch_spinal_twist", "easy"),
        34: ("pcod_stretch_spinal_twist", "med"),
        35: ("pcod_stretch_spinal_twist", "hard"),
    }

    while running:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False

            # input boxes events
            input_name.handle_event(event)
            input_age.handle_event(event)
            input_height.handle_event(event)
            input_weight.handle_event(event)

            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                mx,my = event.pos

                # PAGE 1: Start
                if page == 1 and start_btn.is_clicked(event.pos):
                    page = 2

                # PAGE 2: form next/back
                elif page == 2:
                    if form_next_btn.is_clicked(event.pos):
                        # save user data
                        user_data["name"] = input_name.text.strip()
                        user_data["age"]  = input_age.text.strip()
                        user_data["height"] = input_height.text.strip()
                        user_data["weight"] = input_weight.text.strip()
                        page = 3
                    elif form_back_btn.is_clicked(event.pos):
                        page = 1

                # PAGE 3: choice landing (left/right buttons) + bottom-back to go back to form
                elif page == 3:
                    if sed_btn.is_clicked(event.pos):
                        page = 4
                    elif pcod_btn.is_clicked(event.pos):
                        page = 5
                    elif bottom_back_btn.is_clicked(event.pos):
                        # go to page 2 (form) as requested
                        page = 2
                    else:
                        # Check for quit button click
                        quit_btn_rect = pygame.Rect(
                        SCREEN_SIZE[0] - int(180 * scale_factor),
                        SCREEN_SIZE[1] - int(90 * scale_factor),
                        int(160 * scale_factor),
                        int(56 * scale_factor)
                        )
                        if quit_btn_rect.collidepoint(event.pos):
                            pygame.quit()
                            sys.exit()

                # PAGE 4: sedentary choices (go to difficulty pages instead of benefit)
                elif page == 4:
                    if sed_cardio_btn.is_clicked(event.pos):
                        last_exercise_base = "sed_cardio_step_touch"
                        page = 18  # sed cardio easy difficulty page
                    elif sed_strength_btn.is_clicked(event.pos):
                        last_exercise_base = "sed_strength_side_leg"
                        page = 21  # sed strength easy difficulty page
                    elif sed_stretch_btn.is_clicked(event.pos):
                        last_exercise_base = "sed_stretch_side_stretch"
                        page = 24  # sed stretch easy difficulty page
                    elif bottom_back_btn.is_clicked(event.pos):
                        page = back_page_map.get(4, 3)

                # PAGE 5: pcod choices (go to difficulty pages instead of benefit)
                elif page == 5:
                    if pcod_cardio_btn.is_clicked(event.pos):
                        last_exercise_base = "pcod_cardio_low_march"
                        page = 27  # pcod cardio easy difficulty page
                    elif pcod_strength_btn.is_clicked(event.pos):
                        last_exercise_base = "pcod_strength_squats"
                        page = 30  # pcod strength easy difficulty page
                    elif pcod_stretch_btn.is_clicked(event.pos):
                        last_exercise_base = "pcod_stretch_spinal_twist"
                        page = 33  # pcod stretch easy difficulty page
                    elif bottom_back_btn.is_clicked(event.pos):
                        page = back_page_map.get(5, 3)

                # DIFFICULTY PAGES (18-35): Easy/Med/Hard buttons -> benefit page
                elif page in difficulty_pages:
                    exercise_base, current_diff = difficulty_pages[page]
                    if easy_btn.is_clicked(event.pos):
                        selected_exercise_key = f"{exercise_base}_easy"
                        page = exercise_map[selected_exercise_key]["benefit"]
                    elif med_btn.is_clicked(event.pos):
                        selected_exercise_key = f"{exercise_base}_med"
                        page = exercise_map[selected_exercise_key]["benefit"]
                    elif hard_btn.is_clicked(event.pos):
                        selected_exercise_key = f"{exercise_base}_hard"
                        page = exercise_map[selected_exercise_key]["benefit"]
                    elif bottom_back_btn.is_clicked(event.pos):
                        page = back_page_map.get(page, 3)

                # BENEFIT PAGES (6..11): Next -> corresponding instruction page; Back -> difficulty page
                elif page in (6,7,8,9,10,11):
                    if bottom_next_btn.is_clicked(event.pos):
                        found = None
                        for k,v in exercise_map.items():
                            if v["benefit"] == page:
                                found = (k,v)
                                break
                        if found:
                            key, info = found
                            page = info["instruction"]
                        else:
                            print("[WARN] No matching exercise for benefit page", page)
                    elif bottom_back_btn.is_clicked(event.pos):
                        # Go back to the difficulty page for this exercise
                        for k,v in exercise_map.items():
                            if v["benefit"] == page and selected_exercise_key and k.startswith(last_exercise_base):
                                diff = k.split("_")[-1]
                                if diff == "easy":
                                    page = 18 + (list(exercise_map.keys()).index(k) * 3) % 18  # Simplified back logic
                                elif diff == "med":
                                    page = 19 + (list(exercise_map.keys()).index(k) * 3) % 19
                                else:
                                    page = 20 + (list(exercise_map.keys()).index(k) * 3) % 20
                                break
                        else:
                            page = back_page_map.get(page, page-1)

                # INSTRUCTION PAGES (12..17): Next -> launch the game; Back -> benefit page
                elif page in (12,13,14,15,16,17):
                        if bottom_next_btn.is_clicked(event.pos):
                            found = None
                            for k, v in exercise_map.items():
                                if v["instruction"] == page:
                                    found = (k, v)
                                    break

                            if found:
                                key, info = found
                                folder = info["game_folder"]

                                # debug print so you can see what gets resolved
                                print(f"[DEBUG] Instruction page Next clicked. exercise key='{key}', folder='{folder}'")

                                import os
                                launcher_dir = os.path.dirname(os.path.abspath(__file__))
                                resolved = os.path.abspath(os.path.join(launcher_dir, folder))
                                print(f"[DEBUG] Resolved game folder path = {resolved}")
                                
                                # -------- SAVE CURRENT SESSION DATA FOR GAME ----------
                                session_data = {
                                    "name": user_data["name"],
                                    "age": user_data["age"],
                                    "height": user_data["height"],
                                    "weight": user_data["weight"],
                                    "exercise": key   # identifies which exergame was played
                                }

                                session_file = os.path.join(get_data_dir(), "current_session.json")

                                with open(session_file, "w") as f:
                                    json.dump(session_data, f)
                                # -----------------------------------------------------

                                pygame.display.quit()
                                try:
                                    print(f"[DEBUG] Loading game module from folder: {folder}")
                                    print(f"[DEBUG] App root: {get_app_root()}")
                                    print(f"[DEBUG] Data dir: {get_data_dir()}")

                                    game_module = load_game_module(folder)
                                    print(f"[DEBUG] Game module loaded successfully: {game_module}")
                                    print(f"[DEBUG] Has run_game: {hasattr(game_module, 'run_game')}")
                                    print(f"[DEBUG] Starting game...")

                                    game_module.run_game()
                                    print(f"[DEBUG] Game finished normally")
                                except Exception as e:
                                    print(f"[ERROR] Game crashed: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    # Show error to user
                                    import time
                                    print("\nPress Enter to return to menu...")
                                    input()
                                finally:
                                    print(f"[DEBUG] Reinitializing pygame...")
                                    pygame.display.init()
                                    pygame.font.init()
                                    screen = pygame.display.set_mode(SCREEN_SIZE, pygame.FULLSCREEN)
                                    page = 3
                                    print(f"[DEBUG] Returned to menu (page 3)")



        # DRAW
        screen.fill((50,50,50))
        # draw page background image if exists
        # draw page background image if exists
        if 1 <= page <= 17:
            # normal pages 1-17
            img = images.get(page)
            if img:
                screen.blit(img, (0,0))
        elif page in difficulty_pages:
            # Difficulty pages: use page 4 (SED) or page 5 (PCOD) backgrounds
            bg_page = 4 if page in range(18, 27) else 5  # 18-26=SED, 27-35=PCOD
            img = images.get(bg_page)
            if img:
                screen.blit(img, (0,0))


        mouse_pos = pygame.mouse.get_pos()

        # overlay UI elements depending on page
        if page == 1:
            # show Start button (moved upward)
            start_btn.draw(screen)Remove-Item -Recurse -Force .git

            
        elif page == 2:
            # Draw centered form container with transparency ---
            form_rect = pygame.Rect(form_x, form_y, form_width, form_height)

            # Create a temporary surface with per-pixel alpha
            form_surface = pygame.Surface((form_width, form_height), pygame.SRCALPHA)

            # RGBA color → (R, G, B, Alpha)
            # Alpha 0 = fully transparent, 255 = opaque
            semi_transparent_color = (245, 245, 245, 90)  # adjust 180 for more/less transparency

            # Draw rounded transparent rectangle on form surface
            pygame.draw.rect(form_surface, semi_transparent_color, (0, 0, form_width, form_height), border_radius=12)

            # Add a slightly opaque black border (still visible on any background)
            pygame.draw.rect(form_surface, (0, 0, 0, 200), (0, 0, form_width, form_height), 2, border_radius=12)

            # Now blit (overlay) this semi-transparent surface onto main screen
            screen.blit(form_surface, (form_x, form_y))

            # Title text (draw on main screen, not on form_surface)
            title = FORM_TITLE_FONT.render("Enter details", True, (0,0,0))
            screen.blit(title, (form_x + 20, form_y + 12))

            # labels and inputs (use LABEL_FONT)
            # Name
            name_lbl = LABEL_FONT.render("Name:", True, (0,0,0))
            screen.blit(name_lbl, (input_name.rect.x, input_name.rect.y - int(24*scale_factor)))
            input_name.draw(screen)
            # Age
            age_lbl = LABEL_FONT.render("Age:", True, (0,0,0))
            screen.blit(age_lbl, (input_age.rect.x, input_age.rect.y - int(24*scale_factor)))
            input_age.draw(screen)
            # Height
            height_lbl = LABEL_FONT.render("Height (cm):", True, (0,0,0))
            screen.blit(height_lbl, (input_height.rect.x, input_height.rect.y - int(24*scale_factor)))
            input_height.draw(screen)
            # Weight
            weight_lbl = LABEL_FONT.render("Weight (kg):", True, (0,0,0))
            screen.blit(weight_lbl, (input_weight.rect.x, input_weight.rect.y - int(24*scale_factor)))
            input_weight.draw(screen)

            # Next & Back buttons centered under form
            form_back_btn.draw(screen)
            form_next_btn.draw(screen)

        elif page == 3:
            sed_btn.draw(screen, highlight=sed_btn.rect.collidepoint(mouse_pos))
            pcod_btn.draw(screen, highlight=pcod_btn.rect.collidepoint(mouse_pos))
            # bottom-right Next (go back to form)
            bottom_back_btn.draw(screen, highlight=bottom_back_btn.rect.collidepoint(mouse_pos))
            # Quit button (bottom-right corner)
            quit_btn_rect = pygame.Rect(
            SCREEN_SIZE[0] - int(180 * scale_factor),
            SCREEN_SIZE[1] - int(90 * scale_factor),
            int(160 * scale_factor),
            int(56 * scale_factor)
            )
            quit_btn = Button(rect=quit_btn_rect, text="Quit")
            quit_btn.draw(screen, highlight=quit_btn.rect.collidepoint(mouse_pos))
        elif page == 4:
            # highlight logic: hover OR last_selected_exercise matches
            sed_cardio_btn.draw(screen, highlight=(sed_cardio_btn.rect.collidepoint(mouse_pos) or last_selected_exercise == "sed_cardio_step_touch"))
            sed_strength_btn.draw(screen, highlight=(sed_strength_btn.rect.collidepoint(mouse_pos) or last_selected_exercise == "sed_strength_side_leg"))
            sed_stretch_btn.draw(screen, highlight=(sed_stretch_btn.rect.collidepoint(mouse_pos) or last_selected_exercise == "sed_stretch_side_stretch"))
            bottom_back_btn.draw(screen, highlight=bottom_back_btn.rect.collidepoint(mouse_pos))

        elif page == 5:
            pcod_cardio_btn.draw(screen, highlight=(pcod_cardio_btn.rect.collidepoint(mouse_pos) or last_selected_exercise == "pcod_cardio_low_march"))
            pcod_strength_btn.draw(screen, highlight=(pcod_strength_btn.rect.collidepoint(mouse_pos) or last_selected_exercise == "pcod_strength_squats"))
            pcod_stretch_btn.draw(screen, highlight=(pcod_stretch_btn.rect.collidepoint(mouse_pos) or last_selected_exercise == "pcod_stretch_spinal_twist"))
            bottom_back_btn.draw(screen, highlight=bottom_back_btn.rect.collidepoint(mouse_pos))

        # DIFFICULTY PAGES (18-35)
        elif page in difficulty_pages:
            easy_btn.draw(screen, highlight=easy_btn.rect.collidepoint(mouse_pos))
            med_btn.draw(screen, highlight=med_btn.rect.collidepoint(mouse_pos))
            hard_btn.draw(screen, highlight=hard_btn.rect.collidepoint(mouse_pos))
            bottom_back_btn.draw(screen, highlight=bottom_back_btn.rect.collidepoint(mouse_pos))
            # Show exercise name at top
            exercise_base, _ = difficulty_pages[page]
            exercise_title = BASE_FONT.render(f"Select difficulty for: {exercise_base.replace('_', ' ').title()}", True, (0,0,0))
            screen.blit(exercise_title, (SCREEN_SIZE[0]//2 - exercise_title.get_width()//2, int(120*scale_factor)))

        elif page in (6,7,8,9,10,11):
            bottom_next_btn.draw(screen, highlight=bottom_next_btn.rect.collidepoint(mouse_pos))
            bottom_back_btn.draw(screen, highlight=bottom_back_btn.rect.collidepoint(mouse_pos))
            info_text = BASE_FONT.render("Benefits page - click Next for instructions", True, (0,0,0))
            screen.blit(info_text, (20,20))

        elif page in (12,13,14,15,16,17):
            bottom_next_btn.draw(screen, highlight=bottom_next_btn.rect.collidepoint(mouse_pos))
            bottom_back_btn.draw(screen, highlight=bottom_back_btn.rect.collidepoint(mouse_pos))
            info_text = BASE_FONT.render("Instruction page - click Next to start the exercise game", True, (0,0,0))
            screen.blit(info_text, (20,20))

        # small footer: show current page number
        footer = BASE_FONT.render(f"Page {page}", True, (255,255,255))
        screen.blit(footer, (10, SCREEN_SIZE[1]-int(40*scale_factor)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()