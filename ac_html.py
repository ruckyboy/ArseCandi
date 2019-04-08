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
    final_list = [[] for _ in range(7)]
    days_lst = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    times_lst = ['07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00',
                 '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']
    for index, day in enumerate(days_lst):
        for item in timetable_list:
            if item.get('day') == days_lst[index]:
                final_list[index].append(f"{item.get('duration')}   {item.get('title')}")
        final_list[index].sort()

    # Just for test print ####
    dlg_str = ""
    for i in range(7):
        dlg_str += f'{days_lst[i]}\r'
        for tt in final_list[i]:
            dlg_str += f'{tt}\r'
        print(final_list[i])
    # End test print ########

    # TODO - handle two units in the same lecture {grid view only , it's ok on list}

    dlg_str = "<!DOCTYPE HTML>\r<html>\r<head></head>\r<body>\r"
    dlg_str += f'<p>{venue}: Bookings for week {current_week}, commencing {cw_monday}</p>\r'
    for i in range(7):
        dlg_str += f'<p>\r{days_lst[i]}<br/>\r'
        for tt in final_list[i]:
            dlg_str += f'{tt}<br/>\r'
        dlg_str += '</p>\r'
    dlg_str += '</body>\r</html>'

    list_view = dlg_str

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
    .tb div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;max-width:55px;}
    .tb .tb-baqh{vertical-align:top}
    .tb .tb-lqy6{vertical-align:top}
    .tb .legend{color:#333;background-color:#fff5e6;vertical-align:top;}
    .tb .book{color:#eee;background-color:#0080ff;background-image:linear-gradient(to right,#0080ff, #00A0ff);}
    </style>
    </head>
    """
    grid_view += f"""
    <body style='margin: 0px; overflow: hidden;'>
    <table class="tb">
    <tr>
    <th class="tg-head"">Week {current_week}</th>
    <th class="tg-head" colspan="4">{cw_monday} - {cw_sunday}</th>
    <th class="tg-head" colspan="14">{venue}</th>
    </tr>
    <tr>
    <td class="legend"> </td>"""

    for time_ in times_lst:
        grid_view += f'<td class="legend">{time_}</td>'

    grid_view += f"""
    </tr>
    <tr>
    <td class="legend">Monday</td>
    <td class="legend"> </td>
    <td class="tg-lqy6"> </td>
    <td class="book" colspan="2"><div>sfghsf sfhf hsfg dx gf h hsrth srt h </div></td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    <td class="tg-lqy6"> </td>
    </tr>
    <tr>
    <td class="legend">Tuesday</td>
    <td class="book">Running</td>
    <td></td>
    <td class="book" colspan="2"><div>14:10</div></td>
    <td class="book"><div>15:45</div></td>
    <td class="tg-lqy6">16:00</td>
    <td class="tg-lqy6">16:00</td>
    </tr>
    <tr>
    <td class="legend">Wednesday</td>
    <td class="book"></td>
    <td class="book">70%</td>
    <td class="book">55%</td>
    <td class="book">90%</td>
    <td class="book"><div>  8 8%88% 88%88% 88%88%88% 88%</div></td>
    <td class="book"><div>  8 8%88% 88%88% 88%88%88% 88%</div></td>
    <td class="book" colspan="12"><div>  8 8%88% 88%88% 88%88%88% 88%</div></td>
    </tr>
    </table>
    </body>
    </html>"""

    return grid_view, list_view