"""Timing-console drawing. All calculations and state live elsewhere."""
import pygame
import charts
from track import fit_points,point_at
from replay import progress

BG=(17,21,24)
PANEL=(25,31,35)
LINE=(53,62,68)
TEXT=(236,240,242)
MUTED=(146,160,168)
RED=(220,63,67)
TYRES={'S':(235,79,85),'M':(235,202,76),'H':(225,229,232)}


def panel(app,rect,label):
    pygame.draw.rect(app.screen,PANEL,rect)
    pygame.draw.rect(app.screen,LINE,rect,1)
    app.text(label,rect[0]+20,rect[1]+16,MUTED,True)


def time_label(seconds):
    # Round once before splitting, so 59.9996 carries into the next minute.
    hours, remaining = divmod(round(seconds * 1000), 3_600_000)
    minutes, remaining = divmod(remaining, 60_000)
    whole_seconds, milliseconds = divmod(remaining, 1000)
    return f'{hours}:{minutes:02}:{whole_seconds:02}.{milliseconds:03}'


def draw(app):
    app.screen.fill(BG);app.controls={};app.tooltips=[]
    pygame.draw.rect(app.screen,RED,(24,25,6,38))
    app.screen.blit(app.title.render('PITWALL',True,TEXT),(44,17))
    app.text('RACE ENGINEERING / STRATEGY WORKSTATION',46,66,MUTED,True)
    app.navigation()
    pygame.draw.line(app.screen,LINE,(24,92),(1416,92))
    app.text('CIRCUIT PROFILE',24,102,MUTED,True)
    app.button('profile',f'{app.profile.country}  {app.profile.name.upper()}',(24,126,330,40))
    for key,label,x in [('laps','RACE LAPS',380),('base','BASE s',500),('pit','PIT LOSS s',620),('wear','WEAR x',740)]:
        app.field(key,label,x,102,100)
    app.button('load','Load session',(900,126,155,40))
    app.button('save','Save session',(1070,126,155,40))
    app.button('export','Export CSV',(1240,126,176,40))
    panel(app,(24,184,370,608),'01 / STINT WORKSHEET')
    app.text('Click tyres to cycle. Edit stops after lap.',44,222,MUTED,True)
    for i in range(2):
        y=256+i*174
        app.text(f'PLAN {"AB"[i]}',44,y,RED if i==0 else TEXT)
        count=app.counts[i]
        app.button(f'count{i}',f'{count} stop'+('' if count==1 else 's'),(260,y-5,114,36))
        width=330/(count+1)
        for j in range(count+1):
            compound=app.compounds[i][j]
            app.button(f'tyre{i}{j}',{'S':'Soft','M':'Medium','H':'Hard'}[compound],(44+j*width,y+40,width-5,38),TYRES[compound])
        for j in range(count):
            app.field(f'stop{i}_{j}',f'STOP {j+1} AFTER LAP',44+j*170,y+88,155)
        if not count: app.text('Continuous stint / no tyre change',44,y+109,MUTED,True)
    pygame.draw.line(app.screen,LINE,(44,600),(374,600))
    app.button('advanced','Conditions '+(' / EDIT' if app.advanced else ' / VIEW'),(44,613,330,34))
    if app.advanced:
        app.field('temperature','TRACK C',44,657,95)
        app.button('weather',app.fields['weather'],(154,680,110,38))
        app.field('sc_start','SC START (0 OFF)',44,725,155)
        app.field('sc_duration','SC DURATION',214,725,160)
    else:
        app.text(f'{app.fields["temperature"]} C   /   {app.fields["weather"].upper()}',44,661)
        app.text(f'SC start {app.fields["sc_start"]} / {app.fields["sc_duration"]} laps (0 off)',44,697,MUTED,True)
        app.text('Shared conditions apply to both plans.',44,736,MUTED,True)
        app.text('Illustrative coefficients. Not telemetry.',44,761,MUTED,True)
    draw_track(app)
    draw_results(app)
    draw_chart(app)
    app.button('simulate','SIMULATE',(24,808,178,42),RED)
    app.button('optimise','ONE-STOP / A',(214,808,180,42))
    app.button('play','PAUSE' if app.replay.playing else 'PLAY',(412,808,95,42))
    app.button('restart','Restart',(517,808,100,42))
    app.button('speed',f'{app.replay.speed}x',(627,808,80,42))
    rail=pygame.Rect(724,822,470,16)
    app.controls['timeline']=rail
    pygame.draw.rect(app.screen,LINE,rail)
    fraction=app.replay.elapsed/app.replay.duration if app.replay.duration else 0
    pygame.draw.rect(app.screen,RED,(rail.x,rail.y,rail.width*fraction,rail.height))
    pygame.draw.circle(app.screen,TEXT,(rail.x+rail.width*fraction,rail.centery),5)
    if app.focus == 'timeline':
        pygame.draw.rect(app.screen,RED,rail.inflate(6,6),1)
    app.text(time_label(app.replay.elapsed),1212,820,TEXT)
    app.draw_status();app.present()


def draw_track(app):
    panel(app,(412,184,610,322),'02 / CIRCUIT REPLAY')
    app.text('LIVE' if app.replay.playing else 'PAUSED',920,200,RED if app.replay.playing else MUTED,True)
    bounds=(432,238,570,218)
    for x in range(442,1000,22):
        for y in range(245,455,22): pygame.draw.circle(app.screen,(39,47,52),(x,y),1)
    points=fit_points(app.profile.points,bounds,14)
    pygame.draw.lines(app.screen,(7,10,12),True,points,16)
    pygame.draw.lines(app.screen,(74,84,92),True,points,9)
    pygame.draw.lines(app.screen,(157,169,176),True,points,2)
    app.text('S/F',points[0][0]-25,points[0][1]+10,MUTED,True)
    if app.result:
        for i,result in enumerate((app.result.a,app.result.b)):
            distance,index=progress(result,app.replay.elapsed)
            point=point_at(points,distance)
            color=RED if i==0 else TEXT
            pygame.draw.circle(app.screen,BG,point,10)
            pygame.draw.circle(app.screen,color,point,7 if i==0 else 4)
            app.text('AB'[i],point[0]+12,point[1]-10-i*16,color,True)
            lap=result.laps[index]
            label='FINISHED' if distance>=len(result.laps) else f'L{index+1:02} / {lap.compound} / AGE {lap.age}'
            app.text(f'{"AB"[i]}  {label}',432+i*300,472,color,True)
    else: app.text('Simulate to prepare replay.',432,472,MUTED,True)


def draw_results(app):
    panel(app,(1040,184,376,322),'03 / PROJECTED CLASSIFICATION')
    app.text('NEEDS UPDATE' if app.stale else 'RACE TOTALS',1060,226,RED if app.stale else MUTED,True)
    if not app.result:
        app.text('No current prediction',1060,270)
        return
    r=app.result
    for i,result in enumerate((r.a,r.b)):
        y=258+i*74
        app.text(f'PLAN {"AB"[i]}',1060,y,RED if i==0 else TEXT)
        app.screen.blit(app.numbers.render(time_label(result.total),True,TEXT),(1162,y))
        app.text(f'{result.total:.3f} seconds',1162,y+30,MUTED,True)
    pygame.draw.line(app.screen,LINE,(1060,406),(1396,406))
    verdict='EQUAL PREDICTED TOTALS' if r.winner=='Tie' else f'PLAN {r.winner} ADVANTAGE'
    app.text(verdict,1060,421,MUTED,True)
    app.screen.blit(app.title.render(f'{abs(r.gap):.3f}',True,RED),(1058,444))
    app.text('SECONDS',1300,466,MUTED,True)


def draw_chart(app):
    panel(app,(412,524,1004,268),'04 / STRATEGY TRACE')
    for i,(metric,label) in enumerate((('lap','Lap incl. pits'),('gap','Gap B-A'),('tyre','Degradation'))):
        app.button('metric_'+metric,label,(928+i*158,536,146,34),RED if app.metric==metric else None)
    app.field('pace_a','PACE A s/lap',432,568,130)
    app.field('pace_b','PACE B s/lap',577,568,130)
    app.text('Driver offsets apply to ordinary racing laps.',728,601,MUTED,True)
    if not app.result: return
    groups=charts.series(app.result,app.metric)
    bounds=pygame.Rect(474,652,922,100)
    low,high=charts.limits(groups)
    for fraction in (0,.5,1):
        y=bounds.y+fraction*bounds.height
        pygame.draw.line(app.screen,LINE,(bounds.x,y),(bounds.right,y))
        app.text(f'{high-(high-low)*fraction:.1f}',432,y-8,MUTED,True)
    for i,values in enumerate(groups):
        points=charts.points(values,bounds,(low,high))
        if i==0: pygame.draw.lines(app.screen,RED,False,points,2)
        else:
            for a,b in zip(points,points[1:]):
                # A dotted white trace keeps identical plans distinguishable.
                middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
                pygame.draw.line(app.screen,TEXT,a,middle,2)
    for index in (0,(len(groups[0])-1)//2,len(groups[0])-1):
        x=bounds.x+index/(len(groups[0])-1)*bounds.width
        app.text(str(index+1),x-5,756,MUTED,True)
    if bounds.collidepoint(app.mouse):
        index=charts.hover_index(app.mouse[0],len(groups[0]),bounds)
        x=charts.points(groups[0],bounds,(low,high))[index][0]
        pygame.draw.line(app.screen,MUTED,(x,bounds.y),(x,bounds.bottom))
        app.text(app.chart_readout(index),432,628,TEXT,True)
    else: app.text('Red A / dotted white B. Hover for exact lap values. Gap = cumulative B minus A.',432,628,MUTED,True)
