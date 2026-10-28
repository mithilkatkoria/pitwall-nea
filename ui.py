"""First usable Pygame interface. Calculations remain in model.py."""
import pygame
import charts
from widgets import fit_text, wrap_text
import driver_view
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
        self.screen = pygame.display.set_mode((1400, 900))
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

    def handle(self, event):
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
        if self.view=='notes':
            self.draw_notes()
            return
        if self.view=='drivers':
            driver_view.draw(self)
            return
        self.screen.fill(BG)
        self.controls = {}
        self.tooltips = []
        self.screen.blit(self.title.render('PITWALL',True,TEXT),(30,22))
        self.text('STRATEGY WORKBENCH / FIRST INTERFACE',220,34,MUTED,True)
        self.button('profile',self.profile.name,(700,20,270,42))
        self.navigation()
        for key,label,x in [('laps','Race laps',30),('base','Base seconds',150),('pit','Pit loss seconds',290)]:
            self.field(key,label,x,100,120 if key != 'laps' else 100)
        self.button('advanced','Conditions +',(700,110,270,40))
        for i in range(2):
            y=200+i*78
            self.text(f'PLAN {"AB"[i]}',30,y+12)
            self.button(f'count{i}',f'{self.counts[i]} stop'+('' if self.counts[i]==1 else 's'),(125,y,110,40))
            for j in range(self.counts[i]+1):
                compound=self.compounds[i][j]
                self.button(f'tyre{i}{j}',compound,(260+j*70,y,56,40),TYRES[compound])
            for j in range(self.counts[i]):
                self.field(f'stop{i}_{j}',f'Stop {j+1} after lap',520+j*160,y-20,130)
        self.button('simulate','Simulate both',(30,362,195,42),RED)
        self.button('optimise','Best one-stop A',(240,362,230,42))
        for action,label,x in [('save','Save',500),('load','Load',610),('export','Export CSV',720)]:
            self.button(action,label,(x,362,100 if action!='export' else 120,42))
        if self.advanced:
            for key,label,x in [('wear','Wear x',30),('temperature','Track C',150),('sc_start','SC start (0 off)',300),('sc_duration','SC laps',470),('pace_a','Pace A seconds',600),('pace_b','Pace B seconds',770)]:
                self.field(key,label,x,430,110)
            self.button('weather',self.fields['weather'],(850,362,120,42))
        if self.result:
            y=520 if self.advanced else 445
            r=self.result
            self.text('RESULTS NEED UPDATE' if self.stale else 'PREDICTED TOTALS',30,y-24,RED if self.stale else MUTED,True)
            self.text(f'A   {r.a.total:.3f} s',30,y)
            self.text(f'B   {r.b.total:.3f} s',285,y)
            verdict='Equal predicted totals' if r.winner=='Tie' else f'{r.winner} faster by {abs(r.gap):.3f} s'
            self.text(verdict,545,y,TYRES['M'])
            self.text(f'B minus A: {r.gap:+.3f} s. Lower total wins.',30,y+36,MUTED)
        self.text('S Soft: quicker, wears faster. M Medium: balance. H Hard: slower, lasts longer.',30,760,MUTED,True)
        self.draw_status()
        if not self.advanced and self.result: self.draw_chart()
        self.draw_track()
        self.button('play','Pause' if self.replay.playing else 'Play',(30,790,100,38))
        self.button('restart','Restart',(145,790,110,38))
        self.button('speed',f'{self.replay.speed}x',(270,790,100,38))
        self.text(f'{self.replay.elapsed:.1f} / {self.replay.duration:.1f} s',400,800,MUTED)
        self.controls['timeline']=pygame.Rect(30,840,940,20)
        pygame.draw.rect(self.screen,PANEL,self.controls['timeline'])
        fraction=self.replay.elapsed/self.replay.duration if self.replay.duration else 0
        pygame.draw.rect(self.screen,RED,(30,840,940*fraction,20))
        self.present()

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
                x=min(self.mouse[0]+14,1400-width-10)
                y=max(8,min(self.mouse[1]+24,900-height-8))
                pygame.draw.rect(self.screen,(10,12,14),(x,y,width,height))
                pygame.draw.rect(self.screen,MUTED,(x,y,width,height),1)
                for i,line in enumerate(lines): self.text(line,x+12,y+10+i*20,TEXT,True)
                break
        pygame.display.flip()

    def navigation(self):
        for i,(key,label) in enumerate((('strategy_view','Strategy F1'),('driver_view','Drivers F2'),('notes_view','Model F3'))):
            self.button(key,label,(1000+i*130,20,120,40))

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

    def draw_chart(self):
        labels={'lap':'Lap time incl. pits','gap':'Cumulative B-A','tyre':'Degradation only'}
        for i,(metric,label) in enumerate(labels.items()):
            self.button('metric_'+metric,label,(30+i*235,520,220,36),RED if metric==self.metric else None)
        values=charts.series(self.result,self.metric)
        bounds=pygame.Rect(80,595,880,135)
        low,high=charts.limits(values)
        self.text(f'{high:.2f}',30,590,MUTED,True)
        self.text(f'{low:.2f}',30,715,MUTED,True)
        for fraction in (0,.5,1):
            y=bounds.y+fraction*bounds.height
            pygame.draw.line(self.screen,PANEL,(bounds.x,y),(bounds.right,y))
        for i,group in enumerate(values):
            pygame.draw.lines(self.screen,RED if i==0 else TEXT,False,charts.points(group,bounds,(low,high)),2)
        self.text('L1',80,735,MUTED,True)
        self.text(f'L{len(values[0])}',920,735,MUTED,True)
        if bounds.collidepoint(self.mouse):
            index=charts.hover_index(self.mouse[0],len(values[0]),bounds)
            x=charts.points(values[0],bounds,(low,high))[index][0]
            pygame.draw.line(self.screen,MUTED,(x,bounds.y),(x,bounds.bottom))
            self.text(self.chart_readout(index),30,567,TEXT,True)
        else:
            self.text('Hover for recorded values. Red: A / White: B. Gap: B minus A.',30,567,MUTED,True)

    def draw_track(self):
        panel = pygame.Rect(1000,90,380,570)
        pygame.draw.rect(self.screen,PANEL,panel)
        self.text(self.profile.name.upper(),1020,110)
        self.text(f'{self.profile.length:.3f} km / schematic',1020,145,MUTED,True)
        points=fit_points(self.profile.points,(1000,180,380,430))
        pygame.draw.lines(self.screen,(105,113,121),True,points,13)
        pygame.draw.lines(self.screen,(185,192,199),True,points,2)
        pygame.draw.circle(self.screen,RED,points[0],7)
        self.text('Start / finish. Shared race clock.',1020,625,MUTED,True)
        if self.result:
            for i,result in enumerate((self.result.a,self.result.b)):
                distance,index=progress(result,self.replay.elapsed)
                point=point_at(points,distance)
                color=RED if i==0 else TEXT
                pygame.draw.circle(self.screen,color,point,9 if i==0 else 6)
                self.text('AB'[i],point[0]+12,point[1]-10,color,True)
                label='FINISHED' if distance>=len(result.laps) else f'L{index+1:02} {result.laps[index].compound}'
                self.text(f'{"AB"[i]}  {label}',1020+i*180,675,color,True)


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
