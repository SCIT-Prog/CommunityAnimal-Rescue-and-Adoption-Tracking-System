"""Hand-drawn SVG icon set (24x24, 1.8 stroke) used across the system.
Use in any template:  {{ icon('paw') }}  or  {{ icon('alert', 18, 'red') }}"""
from markupsafe import Markup

_P = {
 'dashboard': '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/><rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/>',
 'inbox': '<path d="M3.5 13.5 6 5.5h12l2.5 8"/><path d="M3.5 13.5v5a1.5 1.5 0 0 0 1.5 1.5h14a1.5 1.5 0 0 0 1.5-1.5v-5h-5l-1.5 2.5h-3L8.5 13.5z"/>',
 'map': '<path d="M12 21s6.5-5.6 6.5-11a6.5 6.5 0 0 0-13 0C5.5 15.4 12 21 12 21z"/><circle cx="12" cy="10" r="2.4"/>',
 'alert': '<path d="M6.5 18v-5a5.5 5.5 0 0 1 11 0v5"/><path d="M4.5 18h15v2.5h-15z"/><path d="M12 3v1.8M4.8 6.3l1.2 1.1M19.2 6.3 18 7.4"/>',
 'paw': '<circle cx="6.3" cy="11" r="1.8"/><circle cx="9.9" cy="6.6" r="1.8"/><circle cx="14.1" cy="6.6" r="1.8"/><circle cx="17.7" cy="11" r="1.8"/><path d="M12 12.4c-3 0-5.2 2.6-5.2 4.6 0 1.8 1.5 2.6 3 2.3.8-.2 1.4-.4 2.2-.4s1.4.2 2.2.4c1.5.3 3-.5 3-2.3 0-2-2.2-4.6-5.2-4.6z"/>',
 'syringe': '<path d="m17 3.5 3.5 3.5M15 5.5l3.5 3.5"/><path d="M18 8.5 9.5 17l-4 1 1-4L15 5.5"/><path d="m8 12.5 3.5 3.5M3.5 20.5 6 18"/>',
 'heart': '<path d="M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.4 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z"/>',
 'users': '<circle cx="9" cy="8" r="3.2"/><path d="M3 19.5c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><circle cx="17" cy="9" r="2.5"/><path d="M17.5 14c2.4.2 4 1.9 4 4.5"/>',
 'user': '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c0-3.6 3-6 7-6s7 2.4 7 6"/>',
 'home': '<path d="M4 11 12 4l8 7"/><path d="M6 10v9.5h12V10"/><path d="M10 19.5v-5h4v5"/>',
 'hand': '<path d="M8 13V6.5a1.3 1.3 0 0 1 2.6 0V11"/><path d="M10.6 5.5a1.3 1.3 0 0 1 2.6 0V11"/><path d="M13.2 6.5a1.3 1.3 0 0 1 2.6 0V12"/><path d="M15.8 8.5a1.3 1.3 0 0 1 2.6 0V14c0 4-2.5 6.5-6 6.5-2.5 0-4-1-5.4-3L4.5 13.5c-.6-1 .6-2.2 1.7-1.5L8 13.5"/>',
 'list': '<rect x="5" y="4.5" width="14" height="16" rx="2"/><path d="M9 4.5h6v2H9z"/><path d="M8.5 11h7M8.5 14.5h7M8.5 18h4"/>',
 'gift': '<rect x="3.5" y="8" width="17" height="4" rx="1"/><path d="M5 12v7.5A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V12M12 8v13"/><path d="M12 8c-1.5 0-3.5-.5-3.5-2.2C8.5 4.6 9.400 4 10.400 4 11.600 4 12 6 12 8c0-2 .4-4 1.600-4 1 0 1.900.6 1.900 1.800C15.500 7.500 13.500 8 12 8z"/>',
 'file': '<path d="M6.5 3.5h7l4.5 4.5v12a1 1 0 0 1-1 1H6.500a1 1 0 0 1-1-1V4.500a1 1 0 0 1 1-1z"/><path d="M13.500 3.500V8H18"/><path d="M9 13h6M9 16.500h6"/>',
 'mail': '<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="m4 7 8 6 8-6"/>',
 'key': '<circle cx="8" cy="15" r="3.5"/><path d="m10.5 12.5 9-9M16 7l2.5 2.5M13.5 9.5l2 2"/>',
 'search': '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.500 4.500"/>',
 'bell': '<path d="M6 16.500v-5a6 6 0 0 1 12 0v5l1.500 2h-15z"/><path d="M10 20.500a2 2 0 0 0 4 0"/>',
 'external': '<path d="M14 4.500h5.500V10M19.500 4.500 11 13"/><path d="M17.500 14v4.500a1.500 1.500 0 0 1-1.500 1.500H6a1.500 1.500 0 0 1-1.500-1.500v-10A1.500 1.500 0 0 1 6 7h4.500"/>',
 'plus': '<path d="M12 5v14M5 12h14"/>',
 'check': '<path d="m5 12.500 4.500 4.500L19 7.500"/>',
 'x': '<path d="M6 6l12 12M18 6 6 18"/>',
 'arrow': '<path d="M5 12h14M13 6l6 6-6 6"/>',
 'back': '<path d="M19 12H5M11 6l-6 6 6 6"/>',
 'calendar': '<rect x="4" y="5.500" width="16" height="14.500" rx="2"/><path d="M4 10h16M8.500 3.500v4M15.500 3.500v4"/>',
 'printer': '<path d="M7 9V4h10v5"/><rect x="4" y="9" width="16" height="8" rx="2"/><path d="M7 14h10v6H7z"/>',
 'edit': '<path d="M4 20h4L18.500 9.500l-4-4L4 16z"/><path d="m12.500 7.500 4 4"/>',
 'trash': '<path d="M4.500 7h15M9.500 7V4.500h5V7M6.500 7l1 13h9l1-13M10 11v5.500M14 11v5.500"/>',
 'moon': '<path d="M20 14.500A8 8 0 0 1 9.500 4a8 8 0 1 0 10.500 10.500z"/>',
 'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.600 5.600 7 7M17 17l1.400 1.400M18.400 5.600 17 7M7 17l-1.400 1.400"/>',
 'palette': '<path d="M12 3.500a8.500 8.500 0 1 0 0 17c1.400 0 2-.9 2-1.800 0-1.200-1-1.500-1-2.600 0-1 .8-1.600 1.800-1.600H17a3.500 3.500 0 0 0 3.500-3.500C20.500 6.700 16.800 3.500 12 3.500z"/><circle cx="8" cy="11" r="1"/><circle cx="11" cy="7.500" r="1"/><circle cx="15.500" cy="8.500" r="1"/>',
 'logout': '<path d="M10 4.500H6A1.500 1.500 0 0 0 4.500 6v12A1.500 1.500 0 0 0 6 19.500h4"/><path d="m15 8 4 4-4 4M19 12H9.500"/>',
 'clock': '<circle cx="12" cy="12" r="8.500"/><path d="M12 7.500V12l3 2"/>',
 'chevron': '<path d="m6 9.500 6 6 6-6"/>',
 'menu': '<path d="M4 7h16M4 12h16M4 17h16"/>',
 'download': '<path d="M12 4v11M7.500 11 12 15.500 16.500 11M5 19.500h14"/>',
 'eye': '<path d="M2.500 12S6 5.500 12 5.500 21.500 12 21.500 12 18 18.500 12 18.500 2.500 12 2.500 12z"/><circle cx="12" cy="12" r="2.800"/>',
 'shield': '<path d="M12 3.500 5 6v5.500c0 4.200 2.800 7.400 7 9 4.200-1.600 7-4.800 7-9V6z"/><path d="m9 12 2.200 2.200L15.500 10"/>',
 'lock': '<rect x="5" y="10.500" width="14" height="9.500" rx="2"/><path d="M8.500 10.500V8a3.500 3.500 0 0 1 7 0v2.500"/>',
 'trend': '<path d="m4 16 5-5 3.500 3.500L20 7M15 7h5v5"/>',
 'filter': '<path d="M4 6h16l-6 7.500V19l-4 1.500v-7z"/>',
 'camera': '<path d="M4 8.500A1.500 1.500 0 0 1 5.500 7H8l1.500-2.500h5L16 7h2.500A1.500 1.500 0 0 1 20 8.500v9a1.500 1.500 0 0 1-1.500 1.500h-13A1.500 1.500 0 0 1 4 17.500z"/><circle cx="12" cy="13" r="3.500"/>',
 'info': '<circle cx="12" cy="12" r="8.500"/><path d="M12 11v5M12 7.800v.1"/>',
 'stethoscope': '<path d="M6 4v5a4 4 0 0 0 8 0V4"/><path d="M10 13v1.500a4.500 4.500 0 0 0 9 0V12"/><circle cx="19" cy="10.500" r="1.800"/>',
 'target': '<circle cx="12" cy="12" r="8.500"/><circle cx="12" cy="12" r="4.500"/><circle cx="12" cy="12" r=".8"/>',
}
# the drawing paths above were typed with a few "x.500" style numbers – normalise them
import re as _re
_P = {k: _re.sub(r'(\d)\.(\d)00\b', r'\1.\2', v) for k, v in _P.items()}

def icon(name, size=20, cls=''):
    body = _P.get(name, _P['paw'])
    return Markup(f'<svg class="ic {cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                  f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{body}</svg>')
