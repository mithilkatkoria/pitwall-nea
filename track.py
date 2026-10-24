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
