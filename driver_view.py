"""Driver analysis rendering, using the application's small drawing helpers."""
import pygame
from analysis import summarise,filtered
from charts import limits


def draw(app):
    app.screen.fill((24,27,30));app.controls={}
    app.text('DRIVER ANALYSIS / seconds',30,25)
    app.navigation()
    app.button('import','Import CSV',(30,80,190,40))
    app.button('sample','Synthetic sample',(235,80,230,40))
    app.button('filter','Exclude pits: '+('ON' if app.exclude_pits else 'OFF'),(480,80,250,40))
    app.text(app.driver_source,30,140,(170,177,184),True)
    summaries=summarise(app.driver_rows,app.exclude_pits)
    names=[row.driver for row in summaries]
    if app.selected_driver not in names: app.selected_driver=names[0] if names else None
    app.driver_page=min(app.driver_page,max(0,(len(summaries)-1)//6))
    app.text('DRIVER                         LAPS      BEST       MEAN       POP. SD      TREND s/lap',30,180)
    for i,row in enumerate(summaries[app.driver_page*6:app.driver_page*6+6]):
        y=220+i*43
        app.button('driver_'+row.driver,row.driver,(30,y,290,36),(220,63,67) if row.driver==app.selected_driver else None)
        for text,x in [(str(row.count),350),(f'{row.best:.3f}',440),(f'{row.mean:.3f}',555),(f'{row.deviation:.3f}',680),(f'{row.trend:+.4f}',820)]:
            app.text(text,x,y+10)
    app.button('previous_drivers','Previous',(1010,220,160,38))
    app.button('next_drivers','Next',(1190,220,160,38))
    app.text(f'Page {app.driver_page+1} / {max(1,(len(summaries)+5)//6)}',1010,270)
    laps=filtered(app.driver_rows,app.selected_driver,app.exclude_pits)
    if laps:
        bounds=pygame.Rect(90,570,1220,210)
        low,high=limits(([row.time for row in laps],))
        first,last=laps[0].lap,laps[-1].lap
        points=[(bounds.x+(row.lap-first)/max(1,last-first)*bounds.width,bounds.bottom-(row.time-low)/(high-low)*bounds.height) for row in laps]
        if len(points)>1: pygame.draw.lines(app.screen,(220,63,67),False,points,2)
        else: pygame.draw.circle(app.screen,(220,63,67),points[0],4)
        app.text(f'{high:.2f}',30,565);app.text(f'{low:.2f}',30,765)
        app.text(f'Lap {first}',90,790);app.text(f'Lap {last}',1230,790)
        app.text(f'{app.selected_driver}: retained lap numbers, including gaps where pit laps are filtered.',30,505)
        if bounds.collidepoint(app.mouse):
            closest=min(range(len(points)),key=lambda index:abs(points[index][0]-app.mouse[0]))
            row=laps[closest]
            app.text(f'Lap {row.lap}: {row.time:.3f} s',30,535)
    else:
        app.text('No laps remain with this filter.',30,520)
    app.text('Population deviation describes this dataset. Trend is linear seconds per lap, not driver ability.',30,835,(170,177,184),True)
    app.text(app.status[:125],30,875,(220,63,67) if app.error else (238,240,242),True)
    pygame.display.flip()
