from datetime import datetime
import ac_json

"""
#########################################################################################
   HTML Generation - move this to it's own .py # TODO
#########################################################################################
"""


def timetable_html(sims_id, venue):
    today_iso = datetime.now().date()
    current_year, current_week, _ = today_iso.isocalendar()
    cw_monday = datetime.strptime(f'{current_year}-{current_week}-1', "%G-%V-%u").strftime('%d/%m/%Y')
    cw_sunday = datetime.strptime(f'{current_year}-{current_week}-7', "%G-%V-%u").strftime('%d/%m/%Y')

    timetable_list = ac_json.build_sims_json(sims_id)
    view_list = [[] for _ in range(7)]
    days_lst = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    times_lst = ['07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00',
                 '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00']
    for index, day in enumerate(days_lst):
        for item in timetable_list:
            if item.get('day') == day:
                view_list[index].append(
                    (item.get("duration"), item.get("title"), item.get('g_start'), item.get('g_span')))
        view_list[index].sort(key=lambda x: x[2])

    # Build the list view html ####
    html_str = "<!DOCTYPE HTML>\r<html>\r<head></head>\r<body>\r"
    html_str += f'<p>{venue}: Bookings for week {current_week}, commencing {cw_monday}</p>\r'
    for i in range(7):
        html_str += f'<p>\r{days_lst[i]}<br/>\r'
        for booking in view_list[i]:
            html_str += f'{booking[0]} &nbsp; {booking[1]}<br/>\r'
        html_str += '</p>\r'
    html_str += '</body>\r</html>'
    # End list view build #########

    list_view = html_str

    # build and populate a 17 x 7 matrix of booking names and column span values
    tt_matrix = [[None for _ in range(17)] for _ in range(7)]
    for i in range(7):
        for booking in view_list[i]:
            tt_matrix[i][booking[2] - 7] = (booking[1], booking[3])
    # NB lectures with multiple attending units will only show the last unit name

    # Build the grid view html ####
    grid_view = """
    <!DOCTYPE HTML>
    <html>
    <head>
    <style type="text/css">
    .tb  {border-collapse:collapse;border-spacing:0px;border-width:0px;border-style:solid;border-color:#aaa;
          margin-left:auto;margin-right:auto;text-align:center;width:100%;}
    .tb td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;
           border-bottom: 1px solid #fff7f7;color:#333;background-color:#fff;width:5.5%;}
    .tb th{font-family:Arial, sans-serif;font-size:16px;font-weight:normal;padding:10px 5px;text-align:left;
           border-style:solid;border-width:0px;overflow:hidden;border-color:#aaa;color:#fff;background-color:#FF9900;}
    .tb div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;max-width:60px;}
    .tb .legend{color:#333;background-color:#fff5e6;vertical-align:top;}
    .tb .book{color:#eee;background-color:#0080ff;background-image:linear-gradient(to right,#0080ff, #00A0ff);}
    </style>
    </head>
    """

    grid_view += f"""
    <body style='margin: 0px; overflow: hidden;'>
    <table class="tb">
    <tr>
    <th> </th>
    <th class="tg-head" colspan="11">{venue}</th>
    <th class="tg-head" colspan="4">{cw_monday} - {cw_sunday}</th>
    <th class="tg-head" colspan="2">Week {current_week}</th>
    </tr>
    <tr>
    <td class="legend"> </td>\r"""

    for time_ in times_lst:
        grid_view += f'    <td class="legend">{time_}</td>\r'

    grid_view += "    </tr>\r"

    for i in range(7):
        grid_view += f"""
    <tr>
    <td class="legend">{days_lst[i]}</td>\r"""
        skip_td = 0
        for j in range(17):
            if skip_td:  # skip drawing td's if colspan has just been used
                skip_td -= 1
                continue
            booking = tt_matrix[i][j]
            if booking:
                if booking[1] > 1:
                    grid_view += f'    <td class="book" colspan="{booking[1]}"><div>{booking[0]}</div></td>\r'
                    skip_td = booking[1] - 1
                else:
                    grid_view += f'    <td class="book"><div>{booking[0]}</div></td>\r'
            else:
                grid_view += f'    <td> </td>\r'
        grid_view += "    </tr>\r"

    grid_view += """
    </table>\r
    </body>\r
    </html>"""

    return grid_view, list_view
