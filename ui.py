"""Application state and input handling. Views and calculations are separate."""
import pygame
import charts
from widgets import fit_text, wrap_text
import driver_view
import strategy_view
from analysis import read_laps, SAMPLE_PATH
from circuits import load_circuits
from track import fit_points, point_at
from replay import Replay, progress
from storage import Session, save_session, load_session, export_laps
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
        self.window = pygame.display.set_mode((1152, 720), pygame.RESIZABLE)
        self.screen = pygame.Surface((1440,900))
        self.viewport = pygame.Rect(0,0,1152,720)
        pygame.display.set_caption("PITWALL | race strategy workstation")
        self.font = pygame.font.SysFont("bahnschrift",20)
        self.small = pygame.font.SysFont("bahnschrift",16)
        self.title = pygame.font.SysFont("bahnschrift",38,bold=True)
        self.numbers = pygame.font.SysFont("consolas",24)
        self.profiles = load_circuits()
        self.profile_index = 0
        self.fields = {}
        self.compounds = [['S', 'H', 'H'], ['M', 'H', 'H']]
        self.counts = [1, 1]
        self.focus = None
        self.select_all = False
        self.stale = True
        self.tooltips = []
        self.controls = {}
        self.advanced = False
        self.view = "strategy"
        self.driver_rows = read_laps(SAMPLE_PATH)
        self.driver_source = "Synthetic demonstration data / 180 laps / not telemetry"
        self.exclude_pits = True
        self.driver_page = 0
        self.selected_driver = None
        self.metric = "lap"
        self.mouse = (0,0)
        self.result = None
        self.replay = Replay()
        self.dragging = False
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
        self.replay = Replay()
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
        self.stale = False
        self.replay = Replay(max(result.a.total,result.b.total))
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

    def import_from(self,path,sample=False):
        try:
            rows=read_laps(path)
        except ValueError as error:
            self.status,self.error=str(error),True
            return False
        self.driver_rows=rows
        self.driver_source='Synthetic demonstration data / not telemetry' if sample else f'Imported CSV: {len(rows)} lap records'
        self.selected_driver=None
        self.driver_page=0
        self.status,self.error='Lap data loaded. Statistics use the selected pit filter.',False
        return True

    def session(self):
        base,laps,plans,pit,conditions,paces=self.inputs()
        return Session(self.profile.key,base,laps,pit,conditions,plans,paces)

    def load_from(self,path):
        try:
            session=load_session(path)
            result=session.validate()
        except ValueError as error:
            self.status,self.error=str(error),True
            return False
        self.set_profile(next(i for i,c in enumerate(self.profiles) if c.key==session.circuit))
        self.fields.update(base=str(session.base),laps=str(session.laps),pit=str(session.pit),
                           wear=str(session.conditions.wear),temperature=str(session.conditions.temperature),
                           weather=session.conditions.weather,sc_start=str(session.conditions.sc_start),
                           sc_duration=str(session.conditions.sc_duration),pace_a=str(session.paces[0]),pace_b=str(session.paces[1]))
        for i,plan in enumerate(session.plans):
            self.counts[i]=len(plan.stops)
            self.compounds[i]=list(plan.compounds)+['H']*(3-len(plan.compounds))
            for j,stop in enumerate(plan.stops): self.fields[f'stop{i}_{j}']=str(stop)
        self.result=result
        self.stale=False
        self.replay=Replay(max(result.a.total,result.b.total))
        self.status,self.error='Session loaded and validated.',False
        return True

    def file_action(self,action):
        try:
            path=choose_path(action)
            if not path: return
            if action=='import':
                self.import_from(path)
            elif action=='load':
                self.load_from(path)
            elif action=='save':
                save_session(path,self.session())
                self.status,self.error='Session saved.',False
            else:
                result=export_laps(path,self.session())
                self.result=result
                self.stale=False
                self.replay=Replay(max(result.a.total,result.b.total))
                self.status,self.error=f'Exported {2*len(result.a.laps)} lap rows.',False
        except (ValueError,RuntimeError) as error:
            self.status,self.error=str(error),True

    def dirty(self):
        self.stale = True
        self.status, self.error = "Settings changed. Simulate to update the results below.", False

    def activate(self, key):
        if key in self.fields and key != 'weather':
            self.focus = key
            self.select_all = True
        else:
            self.focus = None
            self.select_all = False
            if key in ('driver_view','strategy_view','notes_view'):
                self.view={'driver_view':'drivers','strategy_view':'strategy','notes_view':'notes'}[key]
            elif key == 'filter': self.exclude_pits=not self.exclude_pits
            elif key == 'sample': self.import_from(SAMPLE_PATH, sample=True)
            elif key == 'import': self.file_action('import')
            elif key == 'previous_drivers': self.driver_page=max(0,self.driver_page-1)
            elif key == 'next_drivers': self.driver_page+=1
            elif key.startswith('driver_'): self.selected_driver=key[7:]
            elif key.startswith('metric_'): self.metric=key[7:]
            elif key in ('save','load','export'): self.file_action(key)
            elif key == 'play': self.replay.toggle()
            elif key == 'restart': self.replay.restart()
            elif key == 'speed': self.replay.cycle_speed()
            elif key == 'simulate': self.calculate()
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

    def to_logical(self,point):
        return ((point[0]-self.viewport.x)*1440/self.viewport.width,
                (point[1]-self.viewport.y)*900/self.viewport.height)

    def to_window(self,point):
        return (round(self.viewport.x+point[0]*self.viewport.width/1440),
                round(self.viewport.y+point[1]*self.viewport.height/900))

    def handle(self, event):
        if event.type==pygame.VIDEORESIZE:
            self.window=pygame.display.set_mode((max(864,event.w),max(540,event.h)),pygame.RESIZABLE)
            return
        if hasattr(event,'pos'):
            event=pygame.event.Event(event.type,{**event.dict,'pos':self.to_logical(event.pos)})
        if event.type == pygame.MOUSEMOTION: self.mouse = event.pos
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.scrub(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focus = None
            for key, rect in self.controls.items():
                if rect.collidepoint(event.pos):
                    if key == 'timeline':
                        self.dragging = True
                        self.scrub(event.pos[0])
                    else:
                        self.activate(key)
                    break
        elif event.type == pygame.TEXTINPUT and self.focus in self.fields and self.focus != 'weather':
            if self.select_all:
                self.fields[self.focus]='';self.select_all=False
            if len(self.fields[self.focus])+len(event.text) <= 16:
                self.fields[self.focus] += event.text
                self.dirty()
        elif event.type == pygame.KEYDOWN:
            editing=self.focus in self.fields and self.focus!='weather'
            if event.key in (pygame.K_F1,pygame.K_F2,pygame.K_F3):
                self.view={pygame.K_F1:'strategy',pygame.K_F2:'drivers',pygame.K_F3:'notes'}[event.key]
                self.focus=None
            elif event.key == pygame.K_ESCAPE: self.focus = None
            elif event.key == pygame.K_TAB:
                keys=list(self.controls)
                direction=-1 if event.mod & pygame.KMOD_SHIFT else 1
                if keys: self.focus=keys[(keys.index(self.focus)+direction)%len(keys)] if self.focus in keys else keys[0]
                self.select_all=self.focus in self.fields
            elif event.key == pygame.K_RETURN:
                if self.focus in self.controls and not editing: self.activate(self.focus)
                elif self.view=='strategy': self.calculate()
            elif editing and event.key == pygame.K_BACKSPACE:
                self.fields[self.focus]='' if self.select_all else self.fields[self.focus][:-1]
                self.select_all=False;self.dirty()
            elif editing and event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                self.select_all=True
            elif event.mod & pygame.KMOD_CTRL:
                actions={pygame.K_s:'save',pygame.K_l:'load',pygame.K_e:'export',pygame.K_i:'import'}
                if event.key in actions: self.file_action(actions[event.key])
            elif not editing and self.view=='strategy':
                if event.key==pygame.K_SPACE: self.replay.toggle()
                elif event.key==pygame.K_r: self.replay.restart()
                elif event.key==pygame.K_o: self.search()
                elif event.key==pygame.K_c:
                    metrics=('lap','gap','tyre');self.metric=metrics[(metrics.index(self.metric)+1)%3]

    def scrub(self, x):
        rect=self.controls['timeline']
        self.replay.scrub((x-rect.x)/rect.width)

    def update(self, seconds):
        self.replay.advance(seconds)

    def text(self, value, x, y, color=TEXT, small=False):
        self.screen.blit((self.small if small else self.font).render(str(value), True, color), (x,y))

    def button(self, key, label, rect, color=None):
        rect = pygame.Rect(rect)
        self.controls[key] = rect
        pygame.draw.rect(self.screen, (49,54,60) if rect.collidepoint(self.mouse) else PANEL, rect)
        pygame.draw.rect(self.screen, color or (RED if self.focus == key else (75,82,89)), rect, 1)
        shown=fit_text(label,self.font,rect.width-20)
        if shown!=label: self.tooltips.append((rect,label))
        if self.focus==key and self.select_all and key in self.fields:
            pygame.draw.rect(self.screen,(78,63,65),rect.inflate(-8,-8))
        self.text(shown, rect.x+10, rect.y+10, color or TEXT)

    def field(self, key, label, x, y, width=100):
        self.text(label, x,y,MUTED,True)
        self.button(key,self.fields[key],(x,y+23,width,38))

    def draw(self):
        if self.view=='notes': self.draw_notes()
        elif self.view=='drivers': driver_view.draw(self)
        else: strategy_view.draw(self)

    def draw_status(self):
        lines=wrap_text(self.status,self.small,1340)
        for i,line in enumerate(lines[:2]): self.text(line,30,863+i*18,RED if self.error else MUTED,True)
        if len(lines)>2: self.tooltips.append((pygame.Rect(30,861,1340,39),self.status))

    def present(self):
        for rect,label in self.tooltips:
            if rect.collidepoint(self.mouse):
                lines=wrap_text(label,self.small,700)
                width=min(740,max(self.small.size(line)[0] for line in lines)+24)
                height=len(lines)*20+20
                x=min(self.mouse[0]+14,1440-width-10)
                y=max(8,min(self.mouse[1]+24,900-height-8))
                pygame.draw.rect(self.screen,(10,12,14),(x,y,width,height))
                pygame.draw.rect(self.screen,MUTED,(x,y,width,height),1)
                for i,line in enumerate(lines): self.text(line,x+12,y+10+i*20,TEXT,True)
                break
        width,height=self.window.get_size()
        scale=min(width/1440,height/900)
        size=(max(1,round(1440*scale)),max(1,round(900*scale)))
        self.viewport=pygame.Rect((width-size[0])//2,(height-size[1])//2,*size)
        self.window.fill((7,10,12))
        self.window.blit(pygame.transform.smoothscale(self.screen,size),self.viewport)
        pygame.display.flip()

    def navigation(self):
        for i,(key,label) in enumerate((('strategy_view','Strategy F1'),('driver_view','Drivers F2'),('notes_view','Model F3'))):
            self.button(key,label,(800+i*205,25,195,42))

    def draw_notes(self):
        self.screen.fill(BG);self.controls={};self.tooltips=[]
        self.text('MODEL NOTES / assumptions and controls',30,30)
        self.navigation()
        lines=[
            'Purpose: compare educational tyre strategies under the same simplified assumptions.',
            'Ordinary lap = base + compound pace + degradation + fuel + warmup + driver + weather + pit.',
            'Compound pace: Soft 0.00 s / Medium 0.48 s / Hard 1.00 s.',
            'Degradation = (rate x age + 0.018 x max(0, age - life)^2) x wear x (1 + (temperature - 30) x 0.018).',
            'Rates: 0.095 / 0.060 / 0.037. Model lives: 18 / 28 / 38 laps. Age counts completed laps before this lap.',
            'Fuel = (race laps - current lap) x 1.6 x 0.03 seconds. Fresh-tyre warmup = 0.55 seconds.',
            'Weather penalty: Dry 0 / Damp 5 / Wet 14 seconds. Driver pace: -2 to +2 seconds per racing lap.',
            'A pit stop happens after its numbered lap. Next lap starts at age zero, even if pit loss is zero.',
            'Safety car replaces racing terms: base x 1.4 + fuel x 0.25. Tyre age still advances.',
            'SC pit loss = service + 0.6 x transit. Service = min(2.5, configured pit loss).',
            f'Current SC input: start {self.fields["sc_start"]} (0 disables), duration {self.fields["sc_duration"]} laps. Simulate validates the interval.',
            'Optimisation checks 6 x (laps - 1) one-stop plans with two different compounds. It does not optimise two stops.',
            'Ties within 0.00000001 seconds keep the first enumerated plan. Positive B-minus-A means A is faster.',
            'Charts: lap time includes pit loss; tyre chart shows applied degradation only, excluding warmup.',
            'Replay shares elapsed seconds between cars. Schematic movement includes pit time, not a separate pit-lane path.',
            'Driver statistics use population deviation and a least-squares trend against actual lap numbers.',
            'Limits: no traffic, overtaking, random events, physical tyre temperature or real telemetry calibration.',
            'F1/F2/F3 views. Tab/Shift+Tab controls. Enter activate/simulate. Escape clears focus.',
            'When not editing: Space play/pause, R restart, O optimise A, C chart. Ctrl+S/L/E/I save/load/export/import.',
            'Data and formulas are illustrative. Model details are in docs/model.md and data/README.md.'
        ]
        for index,line in enumerate(lines): self.text(line,30,105+index*34,TEXT if index<17 else MUTED,True)
        self.present()

    def chart_readout(self,index):
        values=charts.series(self.result,self.metric)
        label='B-A' if self.metric=='gap' else 'A'
        text=f'Lap {index+1}: {label} {values[0][index]:.3f} s'
        if len(values)==2: text+=f' / B {values[1][index]:.3f} s'
        return text



def choose_path(action):
    from tkinter import Tk, filedialog, TclError
    root=None
    try:
        root=Tk();root.withdraw();root.attributes('-topmost',True)
        if action=='import':
            return filedialog.askopenfilename(parent=root,title='Import driver lap CSV',filetypes=[('Lap data','*.csv')])
        if action=='load':
            return filedialog.askopenfilename(parent=root,title='Load Pitwall session',filetypes=[('Pitwall session','*.json')])
        extension='.csv' if action=='export' else '.json'
        return filedialog.asksaveasfilename(parent=root,title='Export lap data' if action=='export' else 'Save Pitwall session',
                                           defaultextension=extension,filetypes=[('Pitwall file','*'+extension)])
    except TclError as error:
        raise RuntimeError(f'Cannot open file picker: {error}') from error
    finally:
        if root is not None: root.destroy()


def run(frames=None, screenshot=None):
    app=App()
    clock=pygame.time.Clock()
    count=0
    while app.running:
        for event in pygame.event.get(): app.handle(event)
        app.update(min(clock.tick(60)/1000,60))
        app.draw()
        count+=1
        if frames is not None and count >= frames:
            if screenshot: pygame.image.save(app.screen,screenshot)
            break
    pygame.quit()
