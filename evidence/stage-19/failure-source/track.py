"""Pure schematic geometry; no dependency on Pygame."""


def fit_points(points, bounds, padding=30):
    x,y,width,height = bounds
    if width <= 2*padding or height <= 2*padding:
        raise ValueError("Track panel is too small for its padding.")
    xmin,xmax = min(p[0] for p in points),max(p[0] for p in points)
    ymin,ymax = min(p[1] for p in points),max(p[1] for p in points)
    scale = min((width-2*padding)/(xmax-xmin), (height-2*padding)/(ymax-ymin))
    left = x+(width-(xmax-xmin)*scale)/2
    top = y+(height-(ymax-ymin)*scale)/2
    return tuple((left+(px-xmin)*scale, top+(py-ymin)*scale) for px,py in points)


def point_at(points, fraction):
    """Walk the closed polyline by distance rather than vertex count."""
    from math import dist
    edges=list(zip(points,points[1:]+points[:1]))
    lengths=[dist(a,b) for a,b in edges]
    remaining=(fraction % 1)*sum(lengths)
    for (a,b),length in zip(edges,lengths):
        if remaining <= length:
            part=remaining/length
            return a[0]+(b[0]-a[0])*part,a[1]+(b[1]-a[1])*part
        remaining-=length
    return points[0]
