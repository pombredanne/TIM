from lxml import html

from timApp.tests.server.timroutetest import TimRouteTest
from timApp.util.utils import decode_csplugin

diamond_tex = r"""
\begin{tikzpicture}
\node[shape=diamond] {diamond};
\end{tikzpicture}
""".strip()

diamond_svg = f"""
<span class="mathp display"><img style="width:6.93474em; vertical-align:-0.00000em" src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0nVVRGLTgnPz4KPCEtLSBUaGlzIGZpbGUgd2FzIGdlbmVyYXRlZCBieSBkdmlzdmdtIDIuNCAtLT4KPHN2ZyBoZWlnaHQ9JzU3Ljc4OTUxOXB0JyB2ZXJzaW9uPScxLjEnIHZpZXdCb3g9Jy03MiAtNzIgNTcuNzg5NTE5IDU3Ljc4OTUxOScgd2lkdGg9JzU3Ljc4OTUxOXB0JyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHhtbG5zOnhsaW5rPSdodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rJz4KPGRlZnM+CjxwYXRoIGQ9J000LjgxMTk1NSAtMC44ODY2NzVWLTEuNDQ0NTgzSDQuNTYyODg5Vi0wLjg4NjY3NUM0LjU2Mjg4OSAtMC4zMDg4NDIgNC4zMTM4MjMgLTAuMjQ5MDY2IDQuMjA0MjM0IC0wLjI0OTA2NkMzLjg3NTQ2NyAtMC4yNDkwNjYgMy44MzU2MTYgLTAuNjk3Mzg1IDMuODM1NjE2IC0wLjc0NzE5OFYtMi43Mzk3MjZDMy44MzU2MTYgLTMuMTU4MTU3IDMuODM1NjE2IC0zLjU0NjcgMy40NzY5NjEgLTMuOTE1MzE4QzMuMDg4NDE4IC00LjMwMzg2MSAyLjU5MDI4NiAtNC40NjMyNjMgMi4xMTIwOCAtNC40NjMyNjNDMS4yOTUxNDMgLTQuNDYzMjYzIDAuNjA3NzIxIC0zLjk5NTAxOSAwLjYwNzcyMSAtMy4zMzc0ODRDMC42MDc3MjEgLTMuMDM4NjA1IDAuODA2OTc0IC0yLjg2OTI0IDEuMDY2MDAyIC0yLjg2OTI0QzEuMzQ0OTU2IC0yLjg2OTI0IDEuNTI0Mjg0IC0zLjA2ODQ5MyAxLjUyNDI4NCAtMy4zMjc1MjJDMS41MjQyODQgLTMuNDQ3MDczIDEuNDc0NDcxIC0zLjc3NTg0MSAxLjAxNjE4OSAtMy43ODU4MDNDMS4yODUxODEgLTQuMTM0NDk2IDEuNzczMzUgLTQuMjQ0MDg1IDIuMDkyMTU0IC00LjI0NDA4NUMyLjU4MDMyNCAtNC4yNDQwODUgMy4xNDgxOTQgLTMuODU1NTQyIDMuMTQ4MTk0IC0yLjk2ODg2N1YtMi42MDAyNDlDMi42NDAxIC0yLjU3MDM2MSAxLjk0MjcxNSAtMi41NDA0NzMgMS4zMTUwNjggLTIuMjQxNTk0QzAuNTY3ODcgLTEuOTAyODY0IDAuMzE4ODA0IC0xLjM4NDgwNyAwLjMxODgwNCAtMC45NDY0NTFDMC4zMTg4MDQgLTAuMTM5NDc3IDEuMjg1MTgxIDAuMTA5NTg5IDEuOTEyODI3IDAuMTA5NTg5QzIuNTcwMzYxIDAuMTA5NTg5IDMuMDI4NjQzIC0wLjI4ODkxNyAzLjIxNzkzMyAtMC43NTcxNjFDMy4yNTc3ODMgLTAuMzU4NjU1IDMuNTI2Nzc1IDAuMDU5Nzc2IDMuOTk1MDE5IDAuMDU5Nzc2QzQuMjA0MjM0IDAuMDU5Nzc2IDQuODExOTU1IC0wLjA3OTcwMSA0LjgxMTk1NSAtMC44ODY2NzVaTTMuMTQ4MTk0IC0xLjM5NDc3QzMuMTQ4MTk0IC0wLjQ0ODMxOSAyLjQzMDg4NCAtMC4xMDk1ODkgMS45ODI1NjUgLTAuMTA5NTg5QzEuNDk0Mzk2IC0wLjEwOTU4OSAxLjA4NTkyOCAtMC40NTgyODEgMS4wODU5MjggLTAuOTU2NDEzQzEuMDg1OTI4IC0xLjUwNDM1OSAxLjUwNDM1OSAtMi4zMzEyNTggMy4xNDgxOTQgLTIuMzkxMDM0Vi0xLjM5NDc3WicgaWQ9J2cwLTI4Jy8+CjxwYXRoIGQ9J001LjI1MDMxMSAwVi0wLjMwODg0MkM0LjU1MjkyNyAtMC4zMDg4NDIgNC40NzMyMjUgLTAuMzc4NTggNC40NzMyMjUgLTAuODY2NzVWLTYuOTE0MDcyTDMuMDM4NjA1IC02LjgwNDQ4M1YtNi40OTU2NDFDMy43MzU5OSAtNi40OTU2NDEgMy44MTU2OTEgLTYuNDI1OTAzIDMuODE1NjkxIC01LjkzNzczM1YtMy43ODU4MDNDMy41MjY3NzUgLTQuMTQ0NDU4IDMuMDk4MzgxIC00LjQwMzQ4NyAyLjU2MDM5OSAtNC40MDM0ODdDMS4zODQ4MDcgLTQuNDAzNDg3IDAuMzM4NzMgLTMuNDI3MTQ4IDAuMzM4NzMgLTIuMTQxOTY4QzAuMzM4NzMgLTAuODc2NzEyIDEuMzE1MDY4IDAuMTA5NTg5IDIuNDUwODA5IDAuMTA5NTg5QzMuMDg4NDE4IDAuMTA5NTg5IDMuNTM2NzM3IC0wLjIyOTE0MSAzLjc4NTgwMyAtMC41NDc5NDVWMC4xMDk1ODlMNS4yNTAzMTEgMFpNMy43ODU4MDMgLTEuMTc1NTkyQzMuNzg1ODAzIC0wLjk5NjI2NCAzLjc4NTgwMyAtMC45NzYzMzkgMy42NzYyMTQgLTAuODA2OTc0QzMuMzc3MzM1IC0wLjMyODc2NyAyLjkyOTAxNiAtMC4xMDk1ODkgMi41MDA2MjMgLTAuMTA5NTg5QzIuMDUyMzA0IC0wLjEwOTU4OSAxLjY5MzY0OSAtMC4zNjg2MTggMS40NTQ1NDUgLTAuNzQ3MTk4QzEuMTk1NTE3IC0xLjE1NTY2NiAxLjE2NTYyOSAtMS43MjM1MzcgMS4xNjU2MjkgLTIuMTMyMDA1QzEuMTY1NjI5IC0yLjUwMDYyMyAxLjE4NTU1NCAtMy4wOTgzODEgMS40NzQ0NzEgLTMuNTQ2N0MxLjY4MzY4NiAtMy44NTU1NDIgMi4wNjIyNjcgLTQuMTg0MzA5IDIuNjAwMjQ5IC00LjE4NDMwOUMyLjk0ODk0MSAtNC4xODQzMDkgMy4zNjczNzIgLTQuMDM0ODY5IDMuNjc2MjE0IC0zLjU4NjU1QzMuNzg1ODAzIC0zLjQxNzE4NiAzLjc4NTgwMyAtMy4zOTcyNiAzLjc4NTgwMyAtMy4yMTc5MzNWLTEuMTc1NTkyWicgaWQ9J2cwLTQ3Jy8+CjxwYXRoIGQ9J00yLjQ2MDc3MiAwVi0wLjMwODg0MkMxLjgwMzIzOCAtMC4zMDg4NDIgMS43NjMzODcgLTAuMzU4NjU1IDEuNzYzMzg3IC0wLjc0NzE5OFYtNC40MDM0ODdMMC4zNjg2MTggLTQuMjkzODk4Vi0zLjk4NTA1NkMxLjAxNjE4OSAtMy45ODUwNTYgMS4xMDU4NTMgLTMuOTI1MjggMS4xMDU4NTMgLTMuNDM3MTExVi0wLjc1NzE2MUMxLjEwNTg1MyAtMC4zMDg4NDIgMC45OTYyNjQgLTAuMzA4ODQyIDAuMzI4NzY3IC0wLjMwODg0MlYwTDEuNDI0NjU4IC0wLjAyOTg4OEMxLjc3MzM1IC0wLjAyOTg4OCAyLjEyMjA0MiAtMC4wMDk5NjMgMi40NjA3NzIgMFpNMS45MTI4MjcgLTYuMDE3NDM1QzEuOTEyODI3IC02LjI4NjQyNiAxLjY4MzY4NiAtNi41NDU0NTUgMS4zODQ4MDcgLTYuNTQ1NDU1QzEuMDQ2MDc3IC02LjU0NTQ1NSAwLjg0NjgyNCAtNi4yNjY1MDEgMC44NDY4MjQgLTYuMDE3NDM1QzAuODQ2ODI0IC01Ljc0ODQ0MyAxLjA3NTk2NSAtNS40ODk0MTUgMS4zNzQ4NDQgLTUuNDg5NDE1QzEuNzEzNTc0IC01LjQ4OTQxNSAxLjkxMjgyNyAtNS43NjgzNjkgMS45MTI4MjcgLTYuMDE3NDM1WicgaWQ9J2cwLTY2Jy8+CjxwYXRoIGQ9J004LjA5OTYyNiAwVi0wLjMwODg0MkM3LjU4MTU2OSAtMC4zMDg4NDIgNy4zMzI1MDMgLTAuMzA4ODQyIDcuMzIyNTQgLTAuNjA3NzIxVi0yLjUxMDU4NUM3LjMyMjU0IC0zLjM2NzM3MiA3LjMyMjU0IC0zLjY3NjIxNCA3LjAxMzY5OSAtNC4wMzQ4NjlDNi44NzQyMjIgLTQuMjA0MjM0IDYuNTQ1NDU1IC00LjQwMzQ4NyA1Ljk2NzYyMSAtNC40MDM0ODdDNS4xMzA3NiAtNC40MDM0ODcgNC42OTI0MDMgLTMuODA1NzI5IDQuNTIzMDM5IC0zLjQyNzE0OEM0LjM4MzU2MiAtNC4yOTM4OTggMy42NDYzMjYgLTQuNDAzNDg3IDMuMTk4MDA3IC00LjQwMzQ4N0MyLjQ3MDczNSAtNC40MDM0ODcgMi4wMDI0OTEgLTMuOTc1MDkzIDEuNzIzNTM3IC0zLjM1NzQxVi00LjQwMzQ4N0wwLjMxODgwNCAtNC4yOTM4OThWLTMuOTg1MDU2QzEuMDE2MTg5IC0zLjk4NTA1NiAxLjA5NTg5IC0zLjkxNTMxOCAxLjA5NTg5IC0zLjQyNzE0OFYtMC43NTcxNjFDMS4wOTU4OSAtMC4zMDg4NDIgMC45ODYzMDEgLTAuMzA4ODQyIDAuMzE4ODA0IC0wLjMwODg0MlYwTDEuNDQ0NTgzIC0wLjAyOTg4OEwyLjU2MDM5OSAwVi0wLjMwODg0MkMxLjg5MjkwMiAtMC4zMDg4NDIgMS43ODMzMTMgLTAuMzA4ODQyIDEuNzgzMzEzIC0wLjc1NzE2MVYtMi41OTAyODZDMS43ODMzMTMgLTMuNjI2NDAxIDIuNDkwNjYgLTQuMTg0MzA5IDMuMTI4MjY5IC00LjE4NDMwOUMzLjc1NTkxNSAtNC4xODQzMDkgMy44NjU1MDQgLTMuNjQ2MzI2IDMuODY1NTA0IC0zLjA3ODQ1NlYtMC43NTcxNjFDMy44NjU1MDQgLTAuMzA4ODQyIDMuNzU1OTE1IC0wLjMwODg0MiAzLjA4ODQxOCAtMC4zMDg4NDJWMEw0LjIxNDE5NyAtMC4wMjk4ODhMNS4zMzAwMTIgMFYtMC4zMDg4NDJDNC42NjI1MTYgLTAuMzA4ODQyIDQuNTUyOTI3IC0wLjMwODg0MiA0LjU1MjkyNyAtMC43NTcxNjFWLTIuNTkwMjg2QzQuNTUyOTI3IC0zLjYyNjQwMSA1LjI2MDI3NCAtNC4xODQzMDkgNS44OTc4ODMgLTQuMTg0MzA5QzYuNTI1NTI5IC00LjE4NDMwOSA2LjYzNTExOCAtMy42NDYzMjYgNi42MzUxMTggLTMuMDc4NDU2Vi0wLjc1NzE2MUM2LjYzNTExOCAtMC4zMDg4NDIgNi41MjU1MjkgLTAuMzA4ODQyIDUuODU4MDMyIC0wLjMwODg0MlYwTDYuOTgzODExIC0wLjAyOTg4OEw4LjA5OTYyNiAwWicgaWQ9J2cwLTc1Jy8+CjxwYXRoIGQ9J001LjMzMDAxMiAwVi0wLjMwODg0MkM0LjgxMTk1NSAtMC4zMDg4NDIgNC41NjI4ODkgLTAuMzA4ODQyIDQuNTUyOTI3IC0wLjYwNzcyMVYtMi41MTA1ODVDNC41NTI5MjcgLTMuMzY3MzcyIDQuNTUyOTI3IC0zLjY3NjIxNCA0LjI0NDA4NSAtNC4wMzQ4NjlDNC4xMDQ2MDggLTQuMjA0MjM0IDMuNzc1ODQxIC00LjQwMzQ4NyAzLjE5ODAwNyAtNC40MDM0ODdDMi40NzA3MzUgLTQuNDAzNDg3IDIuMDAyNDkxIC0zLjk3NTA5MyAxLjcyMzUzNyAtMy4zNTc0MVYtNC40MDM0ODdMMC4zMTg4MDQgLTQuMjkzODk4Vi0zLjk4NTA1NkMxLjAxNjE4OSAtMy45ODUwNTYgMS4wOTU4OSAtMy45MTUzMTggMS4wOTU4OSAtMy40MjcxNDhWLTAuNzU3MTYxQzEuMDk1ODkgLTAuMzA4ODQyIDAuOTg2MzAxIC0wLjMwODg0MiAwLjMxODgwNCAtMC4zMDg4NDJWMEwxLjQ0NDU4MyAtMC4wMjk4ODhMMi41NjAzOTkgMFYtMC4zMDg4NDJDMS44OTI5MDIgLTAuMzA4ODQyIDEuNzgzMzEzIC0wLjMwODg0MiAxLjc4MzMxMyAtMC43NTcxNjFWLTIuNTkwMjg2QzEuNzgzMzEzIC0zLjYyNjQwMSAyLjQ5MDY2IC00LjE4NDMwOSAzLjEyODI2OSAtNC4xODQzMDlDMy43NTU5MTUgLTQuMTg0MzA5IDMuODY1NTA0IC0zLjY0NjMyNiAzLjg2NTUwNCAtMy4wNzg0NTZWLTAuNzU3MTYxQzMuODY1NTA0IC0wLjMwODg0MiAzLjc1NTkxNSAtMC4zMDg4NDIgMy4wODg0MTggLTAuMzA4ODQyVjBMNC4yMTQxOTcgLTAuMDI5ODg4TDUuMzMwMDEyIDBaJyBpZD0nZzAtNzcnLz4KPHBhdGggZD0nTTQuNjkyNDAzIC0yLjEzMjAwNUM0LjY5MjQwMyAtMy40MDcyMjMgMy42OTYxMzkgLTQuNDYzMjYzIDIuNDkwNjYgLTQuNDYzMjYzQzEuMjQ1MzMgLTQuNDYzMjYzIDAuMjc4OTU0IC0zLjM3NzMzNSAwLjI3ODk1NCAtMi4xMzIwMDVDMC4yNzg5NTQgLTAuODQ2ODI0IDEuMzE1MDY4IDAuMTA5NTg5IDIuNDgwNjk3IDAuMTA5NTg5QzMuNjg2MTc3IDAuMTA5NTg5IDQuNjkyNDAzIC0wLjg2Njc1IDQuNjkyNDAzIC0yLjEzMjAwNVpNMy44NjU1MDQgLTIuMjExNzA2QzMuODY1NTA0IC0xLjg1MzA1MSAzLjg2NTUwNCAtMS4zMTUwNjggMy42NDYzMjYgLTAuODc2NzEyQzMuNDI3MTQ4IC0wLjQyODM5NCAyLjk4ODc5MiAtMC4xMzk0NzcgMi40OTA2NiAtMC4xMzk0NzdDMi4wNjIyNjcgLTAuMTM5NDc3IDEuNjIzOTEgLTAuMzQ4NjkyIDEuMzU0OTE5IC0wLjgwNjk3NEMxLjEwNTg1MyAtMS4yNDUzMyAxLjEwNTg1MyAtMS44NTMwNTEgMS4xMDU4NTMgLTIuMjExNzA2QzEuMTA1ODUzIC0yLjYwMDI0OSAxLjEwNTg1MyAtMy4xMzgyMzIgMS4zNDQ5NTYgLTMuNTc2NTg4QzEuNjEzOTQ4IC00LjAzNDg2OSAyLjA4MjE5MiAtNC4yNDQwODUgMi40ODA2OTcgLTQuMjQ0MDg1QzIuOTE5MDU0IC00LjI0NDA4NSAzLjM0NzQ0NyAtNC4wMjQ5MDcgMy42MDY0NzYgLTMuNTk2NTEzUzMuODY1NTA0IC0yLjU5MDI4NiAzLjg2NTUwNCAtMi4yMTE3MDZaJyBpZD0nZzAtODEnLz4KPC9kZWZzPgo8ZyBpZD0ncGFnZTEnPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKC00My4xMDUyNDcsLTQzLjEwNTI0Nykgc2NhbGUoMSwtMSkiPjxnPgo8ZyBzdHJva2U9InJnYigwLjAlLDAuMCUsMC4wJSkiPgo8ZyBmaWxsPSJyZ2IoMC4wJSwwLjAlLDAuMCUpIj4KPGcgc3Ryb2tlLXdpZHRoPSIwLjRwdCI+CjxnPgo8Zz4KPGc+CjxnIHRyYW5zZm9ybT0ibWF0cml4KDEuMCwwLjAsMC4wLDEuMCwtMTguODk1LC0zLjQxNTAxKSI+CjxnIHN0cm9rZT0icmdiKDAuMCUsMC4wJSwwLjAlKSI+CjxnIGZpbGw9InJnYigwLjAlLDAuMCUsMC4wJSkiPgo8ZyBzdHJva2U9Im5vbmUiIHRyYW5zZm9ybT0ic2NhbGUoLTEsMSkgdHJhbnNsYXRlKC00My4xMDUyNDcsLTQzLjEwNTI0Nykgc2NhbGUoLTEsLTEpIj48dXNlIHg9Jy00My4xMDUyNDcnIHhsaW5rOmhyZWY9JyNnMC00NycgeT0nLTQzLjEwNTI0NycvPgo8dXNlIHg9Jy0zNy41NjYwMjEnIHhsaW5rOmhyZWY9JyNnMC02NicgeT0nLTQzLjEwNTI0NycvPgo8dXNlIHg9Jy0zNC43OTY0MDknIHhsaW5rOmhyZWY9JyNnMC0yOCcgeT0nLTQzLjEwNTI0NycvPgo8dXNlIHg9Jy0yOS44MTUwODknIHhsaW5rOmhyZWY9JyNnMC03NScgeT0nLTQzLjEwNTI0NycvPgo8dXNlIHg9Jy0yMS41MTYyMDgnIHhsaW5rOmhyZWY9JyNnMC04MScgeT0nLTQzLjEwNTI0NycvPgo8dXNlIHg9Jy0xNi41MzQ4ODcnIHhsaW5rOmhyZWY9JyNnMC03NycgeT0nLTQzLjEwNTI0NycvPgo8dXNlIHg9Jy0xMC45OTU2NjInIHhsaW5rOmhyZWY9JyNnMC00NycgeT0nLTQzLjEwNTI0NycvPjwvZz48L2c+CjwvZz4KPC9nPgo8L2c+CjwvZz4KPC9nPgo8L2c+CjwvZz4KPC9nPgo8L2c+CjwvZz48L2c+Cjwvc3ZnPg==" title="{diamond_tex}"></span>
"""

a_plus_b_mathjax = """<span class="math inline">\(a+b\)</span>"""
a_plus_b_svg = """<span class="mathp inline"><img style="width:2.72619em; vertical-align:-0.15963em" src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0nVVRGLTgnPz4KPCEtLSBUaGlzIGZpbGUgd2FzIGdlbmVyYXRlZCBieSBkdmlzdmdtIDIuNCAtLT4KPHN2ZyBoZWlnaHQ9JzguNzQ4NzE3cHQnIHZlcnNpb249JzEuMScgdmlld0JveD0nLTAuNTAwMDAyIC03LjQxODUgMjIuNzE4MjQzIDguNzQ4NzE3JyB3aWR0aD0nMjIuNzE4MjQzcHQnIHhtbG5zPSdodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZycgeG1sbnM6eGxpbms9J2h0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsnPgo8ZGVmcz48c3R5bGUgdHlwZT0idGV4dC9jc3MiPjwhW0NEQVRBW3BhdGgge3N0cm9rZTogY3VycmVudENvbG9yO3N0cm9rZS13aWR0aDogMC4wNXB0O31dXT48L3N0eWxlPjxwYXRoIGQ9J000LjA3NDcyIC0yLjI5MTQwN0g2Ljg1NDI5NkM2Ljk5Mzc3MyAtMi4yOTE0MDcgNy4xODMwNjQgLTIuMjkxNDA3IDcuMTgzMDY0IC0yLjQ5MDY2UzYuOTkzNzczIC0yLjY4OTkxMyA2Ljg1NDI5NiAtMi42ODk5MTNINC4wNzQ3MlYtNS40Nzk0NTJDNC4wNzQ3MiAtNS42MTg5MjkgNC4wNzQ3MiAtNS44MDgyMTkgMy44NzU0NjcgLTUuODA4MjE5UzMuNjc2MjE0IC01LjYxODkyOSAzLjY3NjIxNCAtNS40Nzk0NTJWLTIuNjg5OTEzSDAuODg2Njc1QzAuNzQ3MTk4IC0yLjY4OTkxMyAwLjU1NzkwOCAtMi42ODk5MTMgMC41NTc5MDggLTIuNDkwNjZTMC43NDcxOTggLTIuMjkxNDA3IDAuODg2Njc1IC0yLjI5MTQwN0gzLjY3NjIxNFYwLjQ5ODEzMkMzLjY3NjIxNCAwLjYzNzYwOSAzLjY3NjIxNCAwLjgyNjg5OSAzLjg3NTQ2NyAwLjgyNjg5OVM0LjA3NDcyIDAuNjM3NjA5IDQuMDc0NzIgMC40OTgxMzJWLTIuMjkxNDA3WicgaWQ9J2cxLTQzJy8+CjxwYXRoIGQ9J00zLjcxNjA2NSAtMy43NjU4NzhDMy41MzY3MzcgLTQuMTM0NDk2IDMuMjQ3ODIxIC00LjQwMzQ4NyAyLjc5OTUwMiAtNC40MDM0ODdDMS42MzM4NzMgLTQuNDAzNDg3IDAuMzk4NTA2IC0yLjkzODk3OSAwLjM5ODUwNiAtMS40ODQ0MzNDMC4zOTg1MDYgLTAuNTQ3OTQ1IDAuOTQ2NDUxIDAuMTA5NTg5IDEuNzIzNTM3IDAuMTA5NTg5QzEuOTIyNzkgMC4xMDk1ODkgMi40MjA5MjIgMC4wNjk3MzggMy4wMTg2OCAtMC42Mzc2MDlDMy4wOTgzODEgLTAuMjE5MTc4IDMuNDQ3MDczIDAuMTA5NTg5IDMuOTI1MjggMC4xMDk1ODlDNC4yNzM5NzMgMC4xMDk1ODkgNC41MDMxMTMgLTAuMTE5NTUyIDQuNjYyNTE2IC0wLjQzODM1NkM0LjgzMTg4IC0wLjc5NzAxMSA0Ljk2MTM5NSAtMS40MDQ3MzIgNC45NjEzOTUgLTEuNDI0NjU4QzQuOTYxMzk1IC0xLjUyNDI4NCA0Ljg3MTczMSAtMS41MjQyODQgNC44NDE4NDMgLTEuNTI0Mjg0QzQuNzQyMjE3IC0xLjUyNDI4NCA0LjczMjI1NCAtMS40ODQ0MzMgNC43MDIzNjYgLTEuMzQ0OTU2QzQuNTMzMDAxIC0wLjY5NzM4NSA0LjM1MzY3NCAtMC4xMDk1ODkgMy45NDUyMDUgLTAuMTA5NTg5QzMuNjc2MjE0IC0wLjEwOTU4OSAzLjY0NjMyNiAtMC4zNjg2MTggMy42NDYzMjYgLTAuNTY3ODdDMy42NDYzMjYgLTAuNzg3MDQ5IDMuNjY2MjUyIC0wLjg2Njc1IDMuNzc1ODQxIC0xLjMwNTEwNkMzLjg4NTQzIC0xLjcyMzUzNyAzLjkwNTM1NSAtMS44MjMxNjMgMy45OTUwMTkgLTIuMjAxNzQzTDQuMzUzNjc0IC0zLjU5NjUxM0M0LjQyMzQxMiAtMy44NzU0NjcgNC40MjM0MTIgLTMuODk1MzkyIDQuNDIzNDEyIC0zLjkzNTI0M0M0LjQyMzQxMiAtNC4xMDQ2MDggNC4zMDM4NjEgLTQuMjA0MjM0IDQuMTM0NDk2IC00LjIwNDIzNEMzLjg5NTM5MiAtNC4yMDQyMzQgMy43NDU5NTMgLTMuOTg1MDU2IDMuNzE2MDY1IC0zLjc2NTg3OFpNMy4wNjg0OTMgLTEuMTg1NTU0QzMuMDE4NjggLTEuMDA2MjI3IDMuMDE4NjggLTAuOTg2MzAxIDIuODY5MjQgLTAuODE2OTM2QzIuNDMwODg0IC0wLjI2ODk5MSAyLjAyMjQxNiAtMC4xMDk1ODkgMS43NDM0NjIgLTAuMTA5NTg5QzEuMjQ1MzMgLTAuMTA5NTg5IDEuMTA1ODUzIC0wLjY1NzUzNCAxLjEwNTg1MyAtMS4wNDYwNzdDMS4xMDU4NTMgLTEuNTQ0MjA5IDEuNDI0NjU4IC0yLjc2OTYxNCAxLjY1Mzc5OCAtMy4yMjc4OTVDMS45NjI2NCAtMy44MTU2OTEgMi40MTA5NTkgLTQuMTg0MzA5IDIuODA5NDY1IC00LjE4NDMwOUMzLjQ1NzAzNiAtNC4xODQzMDkgMy41OTY1MTMgLTMuMzY3MzcyIDMuNTk2NTEzIC0zLjMwNzU5N1MzLjU3NjU4OCAtMy4xODgwNDUgMy41NjY2MjUgLTMuMTM4MjMyTDMuMDY4NDkzIC0xLjE4NTU1NFonIGlkPSdnMC05NycvPgo8cGF0aCBkPSdNMi4zODEwNzEgLTYuODA0NDgzQzIuMzgxMDcxIC02LjgxNDQ0NiAyLjM4MTA3MSAtNi45MTQwNzIgMi4yNTE1NTcgLTYuOTE0MDcyQzIuMDIyNDE2IC02LjkxNDA3MiAxLjI5NTE0MyAtNi44MzQzNzEgMS4wMzYxMTUgLTYuODE0NDQ2QzAuOTU2NDEzIC02LjgwNDQ4MyAwLjg0NjgyNCAtNi43OTQ1MjEgMC44NDY4MjQgLTYuNjE1MTkzQzAuODQ2ODI0IC02LjQ5NTY0MSAwLjkzNjQ4OCAtNi40OTU2NDEgMS4wODU5MjggLTYuNDk1NjQxQzEuNTY0MTM0IC02LjQ5NTY0MSAxLjU4NDA2IC02LjQyNTkwMyAxLjU4NDA2IC02LjMyNjI3NkMxLjU4NDA2IC02LjI1NjUzOCAxLjQ5NDM5NiAtNS45MTc4MDggMS40NDQ1ODMgLTUuNzA4NTkzTDAuNjI3NjQ2IC0yLjQ2MDc3MkMwLjUwODA5NSAtMS45NjI2NCAwLjQ2ODI0NCAtMS44MDMyMzggMC40NjgyNDQgLTEuNDU0NTQ1QzAuNDY4MjQ0IC0wLjUwODA5NSAwLjk5NjI2NCAwLjEwOTU4OSAxLjczMzQ5OSAwLjEwOTU4OUMyLjkwOTA5MSAwLjEwOTU4OSA0LjEzNDQ5NiAtMS4zNzQ4NDQgNC4xMzQ0OTYgLTIuODA5NDY1QzQuMTM0NDk2IC0zLjcxNjA2NSAzLjYwNjQ3NiAtNC40MDM0ODcgMi44MDk0NjUgLTQuNDAzNDg3QzIuMzUxMTgzIC00LjQwMzQ4NyAxLjk0MjcxNSAtNC4xMTQ1NyAxLjY0MzgzNiAtMy44MDU3MjlMMi4zODEwNzEgLTYuODA0NDgzWk0xLjQ0NDU4MyAtMy4wMzg2MDVDMS41MDQzNTkgLTMuMjU3NzgzIDEuNTA0MzU5IC0zLjI3NzcwOSAxLjU5NDAyMiAtMy4zODcyOThDMi4wODIxOTIgLTQuMDM0ODY5IDIuNTMwNTExIC00LjE4NDMwOSAyLjc4OTUzOSAtNC4xODQzMDlDMy4xNDgxOTQgLTQuMTg0MzA5IDMuNDE3MTg2IC0zLjg4NTQzIDMuNDE3MTg2IC0zLjI0NzgyMUMzLjQxNzE4NiAtMi42NjAwMjUgMy4wODg0MTggLTEuNTE0MzIxIDIuOTA5MDkxIC0xLjEzNTc0MUMyLjU4MDMyNCAtMC40NjgyNDQgMi4xMjIwNDIgLTAuMTA5NTg5IDEuNzMzNDk5IC0wLjEwOTU4OUMxLjM5NDc3IC0wLjEwOTU4OSAxLjA2NjAwMiAtMC4zNzg1OCAxLjA2NjAwMiAtMS4xMTU4MTZDMS4wNjYwMDIgLTEuMzA1MTA2IDEuMDY2MDAyIC0xLjQ5NDM5NiAxLjIyNTQwNSAtMi4xMjIwNDJMMS40NDQ1ODMgLTMuMDM4NjA1WicgaWQ9J2cwLTk4Jy8+CjwvZGVmcz4KPGcgaWQ9J3BhZ2UxJz4KPHVzZSB4PScwJyB4bGluazpocmVmPScjZzAtOTcnIHk9JzAnLz4KPHVzZSB4PSc3LjQ4MDAyJyB4bGluazpocmVmPScjZzEtNDMnIHk9JzAnLz4KPHVzZSB4PScxNy40NDI2MzMnIHhsaW5rOmhyZWY9JyNnMC05OCcgeT0nMCcvPgo8L2c+Cjwvc3ZnPg==" title="a+b"></span>"""

mathjax_html = f"""
<div tabindex="0" class="parContent">
    <p>{a_plus_b_mathjax}
    </p>
</div>
"""

svg_html = f"""
<div tabindex="0" class="parContent">
    <p>{a_plus_b_svg}
    </p>
</div>
"""


class MathTest(TimRouteTest):

    def test_svg_math(self):
        self.login_test1()
        d = self.create_doc(initial_par="$a+b$")
        d.document.set_settings({'math_type': 'svg'})
        self.assert_same_html(self.get(d.url, as_tree=True).cssselect('.parContent')[1], f"""
<div tabindex="0" class="parContent">
    <p>{a_plus_b_svg}
    </p>
</div>
""")
        return d

    def test_mathjax_math(self):
        self.login_test1()
        d = self.create_doc(initial_par="$a+b$")
        d.document.set_settings({'math_type': 'mathjax'})
        self.assert_same_html(self.get(d.url, as_tree=True).cssselect('.parContent')[1], mathjax_html)
        d.document.set_settings({'math_type': 'xxx'})
        self.assert_same_html(self.get(d.url, as_tree=True).cssselect('.parContent')[1], mathjax_html)
        d.document.set_settings({'math_type': None})
        self.assert_same_html(self.get(d.url, as_tree=True).cssselect('.parContent')[1], mathjax_html)

    def test_mathtype_change(self):
        d = self.test_svg_math()
        d.document.set_settings({'math_type': 'mathjax'})
        self.assert_same_html(self.get(d.url, as_tree=True).cssselect('.parContent')[1], mathjax_html)

    def test_math_preamble(self):
        self.login_test1()
        d = self.create_doc(initial_par=rf"""
$${diamond_tex}$$""")
        d.document.set_settings({'math_type': 'svg', 'math_preamble': r"""
\usetikzlibrary{shapes}
        """})
        self.assert_same_html(self.get(d.url, as_tree=True).cssselect('.parContent > p > span')[0], diamond_svg)

    def test_math_preamble_single_par(self):
        self.login_test1()
        d = self.create_doc(initial_par=r"""
#- {math_type=svg math_preamble="\\usetikzlibrary{shapes}"}
""" f"""{diamond_tex}""")
        t = self.get(d.url, as_tree=True)
        self.assert_same_html(t.cssselect('.parContent > span')[0], diamond_svg)

    def test_math_plugin(self):
        self.login_test1()
        d = self.create_doc(initial_par=r"""
#- {math_type=svg plugin=csPlugin}
stem: 'md: $a+b$'

#- {plugin=csPlugin}
stem: 'md: $a+b$'
""")
        t = self.get(d.url, as_tree=True)
        plugins = t.cssselect('cs-runner')
        for plugin, e in zip(plugins, [a_plus_b_svg, a_plus_b_mathjax]):
            stem = decode_csplugin(plugin)['stem']
            self.assert_same_html(html.fromstring(stem), e)

    def test_mixed_settings(self):
        self.login_test1()
        d = self.create_doc(initial_par=r"""
#- {math_preamble="\\newcommand{\\nothing}{}"}
$a+b$""")
        d.document.set_settings({'math_type': 'svg'})
        t = self.get(d.url, as_tree=True)
        self.assert_same_html(t.cssselect('.parContent')[1], svg_html)
