"""Small text layout helpers shared by the Pygame views."""


def fit_text(text,font,width):
    if font.size(text)[0]<=width: return text
    suffix='...'
    while text and font.size(text+suffix)[0]>width: text=text[:-1]
    return text+suffix if font.size(suffix)[0]<=width else ''


def wrap_text(text,font,width):
    lines=[];current=''
    for word in text.split():
        candidate=(current+' '+word).strip()
        if font.size(candidate)[0]<=width:
            current=candidate
            continue
        if current: lines.append(current);current=''
        for char in word:
            if current and font.size(current+char)[0]>width:
                lines.append(current);current=''
            current+=char
    if current: lines.append(current)
    return lines or ['']
