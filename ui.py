"""First usable Pygame interface. Calculations remain in model.py."""
import pygame
from circuits import load_circuits
from track import fit_points
from model import Strategy, Conditions, compare, optimise

BG = (24, 27, 30)
PANEL = (38, 42, 46)
TEXT = (238, 240, 242)
MUTED = (170, 177, 184)
RED = (220, 63, 67)
TYRES = {'S': (235, 79, 85), 'M': (235, 202, 76), 'H': (225, 229, 232)}


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1400, 760))
        pygame.display.set_caption("PITWALL | circuit workbench")
        self.font = pygame.font.Font(None, 25)
        self.small = pygame.font.Font(None, 21)
        self.title = pygame.font.Font(None, 42)
        self.profiles = load_circuits()
        self.profile_index = 0
        self.fields = {}
        self.compounds = [['S', 'H', 'H'], ['M', 'H', 'H']]
        self.counts = [1, 1]
        self.focus = None
        self.controls = {}
        self.advanced = False
        self.result = None
        self.status = "Choose tyres and stops, then simulate. Stops occur after the numbered lap."
        self.error = False
        self.running = True
        self.set_profile(0)
        self.calculate()

    @property
    def profile(self):
        return self.profiles[self.profile_index]

    def set_profile(self, index):
        self.profile_index = index
        c = self.profile
        self.fields.update(laps=str(c.laps), base=str(c.base_time), pit=str(c.pit_loss), wear=str(c.wear),
                           temperature='30', weather='Dry', sc_start='0', sc_duration='3', pace_a='0', pace_b='0')
        for i in range(2):
            self.fields[f'stop{i}_0'] = str(c.laps//2)
            self.fields[f'stop{i}_1'] = str(2*c.laps//3)
        self.result = None
        self.focus = None
        self.status = f"{c.name} defaults loaded. Simulate to update the results."

    def inputs(self):
        try:
            laps = int(self.fields['laps'])
            base, pit = float(self.fields['base']), float(self.fields['pit'])
            conditions = Conditions(float(self.fields['wear']), int(self.fields['temperature']), self.fields['weather'],
                                    int(self.fields['sc_start']), int(self.fields['sc_duration']))
            plans = tuple(Strategy(tuple(self.compounds[i][:self.counts[i]+1]),
                                   tuple(int(self.fields[f'stop{i}_{j}']) for j in range(self.counts[i]))) for i in range(2))
            paces = (float(self.fields['pace_a']), float(self.fields['pace_b']))
        except (ValueError, OverflowError) as error:
            raise ValueError("Enter numbers in the numeric fields; laps and stops must be whole numbers.") from error
        return base, laps, plans, pit, conditions, paces

    def calculate(self):
        try:
            base, laps, plans, pit, conditions, paces = self.inputs()
            result = compare(base, laps, *plans, pit, conditions, *paces)
        except ValueError as error:
            self.status, self.error = str(error), True
            return False
        self.result = result
        self.status, self.error = "Results updated. Positive B-A means A is faster. Illustrative model, not telemetry.", False
        return True

    def search(self):
        try:
            base, laps, plans, pit, conditions, paces = self.inputs()
            # Validate the whole visible configuration before replacing A.
            compare(base, laps, *plans, pit, conditions, *paces)
            found = optimise(base, laps, pit, conditions, paces[0])
        except ValueError as error:
            self.status, self.error = str(error), True
            return
        self.counts[0] = 1
        self.compounds[0][:2] = found.best.plan.compounds
        self.fields['stop0_0'] = str(found.best.plan.stops[0])
        self.calculate()
        self.status = f"A optimised across {len(found.candidates)} different-compound one-stop plans. Ties keep the first."

    def dirty(self):
        self.status, self.error = "Settings changed. Simulate to update the results below.", False

    def activate(self, key):
        if key in self.fields and key != 'weather':
            self.focus = key
        else:
            self.focus = None
            if key == 'simulate': self.calculate()
            elif key == 'optimise': self.search()
            elif key == 'profile': self.set_profile((self.profile_index+1) % len(self.profiles))
            elif key == 'advanced': self.advanced = not self.advanced
            elif key == 'weather':
                weather = ['Dry','Damp','Wet']
                self.fields[key] = weather[(weather.index(self.fields[key])+1)%3]
                self.dirty()
            elif key.startswith('count'):
                i = int(key[-1]); self.counts[i] = (self.counts[i]+1)%3; self.dirty()
            elif key.startswith('tyre'):
                i,j = map(int,key[-2:]); choices = 'SMH'
                self.compounds[i][j] = choices[(choices.index(self.compounds[i][j])+1)%3]; self.dirty()

    def handle(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focus = None
            for key, rect in self.controls.items():
                if rect.collidepoint(event.pos):
                    self.activate(key)
                    break
        elif event.type == pygame.TEXTINPUT and self.focus:
            if len(self.fields[self.focus])+len(event.text) <= 16:
                self.fields[self.focus] += event.text
                self.dirty()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.focus = None
            elif event.key == pygame.K_RETURN: self.calculate()
            elif event.key == pygame.K_TAB:
                keys = [key for key in self.controls if key in self.fields and key != 'weather']
                self.focus = keys[(keys.index(self.focus)+1)%len(keys)] if self.focus in keys else keys[0]
            elif self.focus and event.key == pygame.K_BACKSPACE:
                self.fields[self.focus] = self.fields[self.focus][:-1]; self.dirty()
            elif self.focus and event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                self.fields[self.focus] = ''; self.dirty()

    def text(self, value, x, y, color=TEXT, small=False):
        self.screen.blit((self.small if small else self.font).render(str(value), True, color), (x,y))

    def button(self, key, label, rect, color=None):
        rect = pygame.Rect(rect)
        self.controls[key] = rect
        pygame.draw.rect(self.screen, PANEL, rect)
        pygame.draw.rect(self.screen, color or (RED if self.focus == key else (75,82,89)), rect, 1)
        self.text(label, rect.x+10, rect.y+10, color or TEXT)

    def field(self, key, label, x, y, width=100):
        self.text(label, x,y,MUTED,True)
        self.button(key,self.fields[key],(x,y+23,width,38))

    def draw(self):
        self.screen.fill(BG)
        self.controls = {}
        self.screen.blit(self.title.render('PITWALL',True,TEXT),(30,22))
        self.text('STRATEGY WORKBENCH / FIRST INTERFACE',220,34,MUTED,True)
        self.button('profile',self.profile.name,(700,20,270,42))
        for key,label,x in [('laps','Race laps',30),('base','Base seconds',150),('pit','Pit loss seconds',290)]:
            self.field(key,label,x,100,120 if key != 'laps' else 100)
        self.button('advanced','Conditions +',(700,110,270,40))
        for i in range(2):
            y=200+i*78
            self.text(f'PLAN {"AB"[i]}',30,y+12)
            self.button(f'count{i}',f'{self.counts[i]} stops',(125,y,110,40))
            for j in range(self.counts[i]+1):
                compound=self.compounds[i][j]
                self.button(f'tyre{i}{j}',compound,(260+j*70,y,56,40),TYRES[compound])
            for j in range(self.counts[i]):
                self.field(f'stop{i}_{j}',f'Stop {j+1} after lap',520+j*160,y-20,130)
        self.button('simulate','Simulate both',(30,362,195,42),RED)
        self.button('optimise','Best one-stop A',(240,362,230,42))
        if self.advanced:
            for key,label,x in [('wear','Wear x',30),('temperature','Track C',150),('sc_start','SC start (0 off)',300),('sc_duration','SC laps',470),('pace_a','Pace A seconds',600),('pace_b','Pace B seconds',770)]:
                self.field(key,label,x,430,110)
            self.button('weather',self.fields['weather'],(850,362,120,42))
        if self.result:
            y=520 if self.advanced else 445
            r=self.result
            self.text(f'A   {r.a.total:.3f} s',30,y)
            self.text(f'B   {r.b.total:.3f} s',285,y)
            verdict='Equal predicted totals' if r.winner=='Tie' else f'{r.winner} faster by {abs(r.gap):.3f} s'
            self.text(verdict,545,y,TYRES['M'])
            self.text(f'B minus A: {r.gap:+.3f} s. Lower total wins.',30,y+36,MUTED)
        self.text('S Soft: quicker, wears faster. M Medium: balance. H Hard: slower, lasts longer.',30,580,MUTED,True)
        self.text(self.status[:115],30,615,RED if self.error else TEXT,True)
        self.draw_track()
        pygame.display.flip()

    def draw_track(self):
        panel = pygame.Rect(1000,90,380,570)
        pygame.draw.rect(self.screen,PANEL,panel)
        self.text(self.profile.name.upper(),1020,110)
        self.text(f'{self.profile.length:.3f} km / schematic',1020,145,MUTED,True)
        points=fit_points(self.profile.points,(1000,180,380,430))
        pygame.draw.lines(self.screen,(105,113,121),True,points,13)
        pygame.draw.lines(self.screen,(185,192,199),True,points,2)
        pygame.draw.circle(self.screen,RED,points[0],7)
        self.text('Start / finish',1020,625,MUTED,True)


def run(frames=None, screenshot=None):
    app=App()
    clock=pygame.time.Clock()
    count=0
    while app.running:
        for event in pygame.event.get(): app.handle(event)
        app.draw()
        count+=1
        if frames is not None and count >= frames:
            if screenshot: pygame.image.save(app.screen,screenshot)
            break
        clock.tick(60)
    pygame.quit()
