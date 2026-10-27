"""Graph values and scaling, independent of display state."""


def series(comparison, metric):
    if metric == 'gap': return (comparison.gaps,)
    field={'lap':'time','tyre':'degradation'}.get(metric)
    if field is None: raise ValueError('Unknown graph metric.')
    return tuple(tuple(getattr(lap,field) for lap in result.laps) for result in (comparison.a,comparison.b))


def limits(groups):
    values=[value for group in groups for value in group]
    low,high=min(values),max(values)
    padding=max((high-low)*.08,.05)
    return low-padding,high+padding


def points(values,bounds,y_range):
    x,y,width,height=bounds
    low,high=y_range
    return tuple((x+i*width/max(1,len(values)-1),y+height-(value-low)/(high-low)*height) for i,value in enumerate(values))


def hover_index(x,count,bounds):
    left,top,width,height=bounds
    return max(0,min(count-1,round((x-left)/width*(count-1))))
