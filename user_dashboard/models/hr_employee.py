from collections import defaultdict
from datetime import timedelta, datetime, date
import pandas as pd
from dateutil.relativedelta import relativedelta
from pytz import utc
from odoo import api, fields, models, _
from odoo.http import request
from odoo.tools import float_utils

ROUNDING_FACTOR = 16


class HrEmployee(models.Model):
    """Inherit hr employee for adding custom fields"""
    _inherit = 'hr.employee'

    birthday = fields.Date(string='Date of Birth', groups="base.group_user",
                           help="Birthday")

    def attendance_manual(self):
        """Manually record attendance for the current employee"""

        employee = request.env['hr.employee'].sudo().browse(
            request.session.uid)
        employee.sudo()._attendance_action_change({
            'city': request.geoip.city.name or _('Unknown'),
            'country_name': request.geoip.country.name or
                            request.geoip.continent.name or _('Unknown'),
            'latitude': request.geoip.location.latitude or False,
            'longitude': request.geoip.location.longitude or False,
            'ip_address': request.geoip.ip,
            'browser': request.httprequest.user_agent.browser,
            'mode': 'kiosk'
        })
        print("context===================",self.env.context)
        return employee

    @api.model
    def check_user_group(self):
        """ Check if the user belongs to the 'hr.group_hr_manager' group.
           Returns: 
           bool: True if the user is in the 'hr.group_hr_manager' group,
               False otherwise.
        """
        uid = request.session.uid
        user = self.env['res.users'].sudo().search([('id', '=', uid)], limit=1)
        if user.has_group('hr.group_hr_manager'):
            return True
        else:
            return False

    @api.model
    def get_user_employee_details(self):
        """
           Get details related to the logged-in user's
        """
        uid = request.session.uid
        employee = self.env['hr.employee'].sudo().search_read(
            [('user_id', '=', uid)], limit=1)
        leaves_to_approve = self.env['hr.leave'].sudo().search_count(
            [('state', 'in', ['confirm', 'validate1'])])
        today = datetime.strftime(datetime.today(), '%Y-%m-%d')
        query = """
        select count(id)
        from hr_leave
        WHERE (hr_leave.date_from::DATE,hr_leave.date_to::DATE) 
        OVERLAPS ('%s', '%s') and
        state='validate'""" % (today, today)
        cr = self._cr
        cr.execute(query)
        leaves_today = cr.fetchall()
        first_day = date.today().replace(day=1)
        last_day = (date.today() + relativedelta(months=1, day=1)) - timedelta(
            1)
        query = """
                select count(id)
                from hr_leave
                WHERE (hr_leave.date_from::DATE,hr_leave.date_to::DATE) 
                OVERLAPS ('%s', '%s')
                and  state='validate'""" % (first_day, last_day)
        cr = self._cr
        cr.execute(query)
        leaves_this_month = cr.fetchall()
        leaves_alloc_req = self.env['hr.leave.allocation'].sudo().search_count(
            [('state', 'in', ['confirm', 'validate1'])])
        timesheet_count = self.env['account.analytic.line'].sudo().search_count(
            [('project_id', '!=', False), ('user_id', '=', uid)])
        timesheet_view_id = self.env.ref(
            'hr_timesheet.hr_timesheet_line_search')
        job_applications = self.env['hr.applicant'].sudo().search_count([])
        if employee:
            if employee[0]['birthday']:
                diff = relativedelta(datetime.today(), employee[0]['birthday'])
                age = diff.years
            else:
                age = False
            if employee:
                data = {
                    'leaves_to_approve': leaves_to_approve,
                    'leaves_today': leaves_today,
                    'leaves_this_month': leaves_this_month,
                    'leaves_alloc_req': leaves_alloc_req,
                    'emp_timesheets': timesheet_count,
                    'job_applications': job_applications,
                    'timesheet_view_id': timesheet_view_id,
                    'age': age
                }
                employee[0].update(data)
            return employee
        else:
            return False

    @api.model
    def get_upcoming(self):
        """Retrieve upcoming events, birthdays, and announcements.
        """
        cr = self._cr
        uid = request.session.uid
        employee = self.env['hr.employee'].search([('user_id', '=', uid)],
                                                  limit=1)
        cr.execute("""select *,
        (to_char(dob,'ddd')::int-to_char(now(),'ddd')::int+
        total_days)%total_days as dif
        from (select he.id, he.name, to_char(he.birthday, 'Month dd') 
        as birthday, hj.name as job_id , he.birthday as dob,
        (to_char((to_char(now(),'yyyy')||'-12-31')::date,'ddd')::int) as 
        total_days FROM hr_employee he
        join hr_job hj on hj.id = he.job_id) birth
        where (to_char(dob,'ddd')::int-to_char(now(),'DDD')::int+
        total_days)%total_days between 0 and 15 order by dif;""")
        birthday = cr.fetchall()
        lang = f"'{self.env.context['lang']}'"
        cr.execute("""select  e.name ->> e.lang as name, e.date_begin,
         e.date_end,rp.name as location
        from event_event e
        inner join res_partner rp
        on e.address_id = rp.id
        and (e.date_begin >= now())
        order by e.date_begin""")
        event = cr.fetchall()
        return {
            'birthday': birthday,
            'event': event,
        }

    @api.model
    def get_dept_employee(self):
        """
           Get the count of employees per department.
        """
        cr = self._cr
        cr.execute("""select department_id, hr_department.name,count(*)
        from hr_employee join hr_department on 
        hr_department.id=hr_employee.department_id
        group by hr_employee.department_id,hr_department.name""")
        dat = cr.fetchall()
        data = []
        for i in range(0, len(dat)):
            data.append(
                {'label': list(dat[i][1].values())[0], 'value': dat[i][2]})
        return data

    @api.model
    def get_department_leave(self):
        """
           Retrieve department-wise leave statistics for the last six months.
        """
        month_list = []
        graph_result = []
        for i in range(5, -1, -1):
            last_month = datetime.now() - relativedelta(months=i)
            text = format(last_month, '%B %Y')
            month_list.append(text)
        self.env.cr.execute(
            """select id, name from hr_department where active=True """)
        departments = self.env.cr.dictfetchall()
        department_list = [list(x['name'].values())[0] for x in departments]
        for month in month_list:
            leave = {}
            for dept in departments:
                leave[list(dept['name'].values())[0]] = 0
            vals = {
                'l_month': month,
                'leave': leave
            }
            graph_result.append(vals)
        sql = """
        SELECT h.id, h.employee_id,h.department_id
             , extract('month' FROM y)::int AS leave_month
             , to_char(y, 'Month YYYY') as month_year
             , GREATEST(y                    , h.date_from) AS date_from
             , LEAST   (y + interval '1 month', h.date_to)   AS date_to
        FROM  (select * from hr_leave where state = 'validate') h
             , generate_series(date_trunc('month', date_from::timestamp)
                             , date_trunc('month', date_to::timestamp)
                             , interval '1 month') y
        where date_trunc('month', GREATEST(y , h.date_from)) >= 
        date_trunc('month', now()) - interval '6 month' and
        date_trunc('month', GREATEST(y , h.date_from)) <= 
        date_trunc('month', now())
        and h.department_id is not null
        """
        self.env.cr.execute(sql)
        results = self.env.cr.dictfetchall()
        leave_lines = []
        for line in results:
            employee = self.browse(line['employee_id'])
            from_dt = fields.Datetime.from_string(line['date_from'])
            to_dt = fields.Datetime.from_string(line['date_to'])
            days = employee.get_work_days_dashboard(from_dt, to_dt)
            line['days'] = days
            vals = {
                'department': line['department_id'],
                'l_month': line['month_year'],
                'days': days
            }
            leave_lines.append(vals)
        if leave_lines:
            df = pd.DataFrame(leave_lines)
            rf = df.groupby(['l_month', 'department']).sum()
            result_lines = rf.to_dict('index')
            for month in month_list:
                for line in result_lines:
                    if month.replace(' ', '') == line[0].replace(' ', ''):
                        match = list(filter(lambda d: d['l_month'] in [month],
                                            graph_result))[0]['leave']
                        dept_name = self.env['hr.department'].browse(
                            line[1]).name
                        if match:
                            match[dept_name] = result_lines[line]['days']
        for result in graph_result:
            result['l_month'] = result['l_month'].split(' ')[:1][0].strip()[
                                :3] + " " + \
                                result['l_month'].split(' ')[1:2][0]

        return graph_result, department_list

    def get_work_days_dashboard(self, from_datetime, to_datetime,
                                compute_leaves=False, calendar=None,
                                domain=None):
        """
               Calculate workdays between two datetime objects.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id

        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)
        intervals = calendar._attendance_intervals_batch(from_full, to_full,
                                                         resource)
        day_total = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_total[start.date()] += (stop - start).total_seconds() / 3600
        if compute_leaves:
            intervals = calendar._work_intervals_batch(from_datetime,
                                                       to_datetime, resource,
                                                       domain)
        else:
            intervals = calendar._attendance_intervals_batch(from_datetime,
                                                             to_datetime,
                                                             resource)
        day_hours = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_hours[start.date()] += (stop - start).total_seconds() / 3600
        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[
                day]) / ROUNDING_FACTOR
            for day in day_hours
        )
        return days

    @api.model
    def employee_leave_trend(self):
        """Generate a trend of employee leaves over the last six months."""
        leave_lines = []
        month_list = []
        graph_result = []
        for i in range(5, -1, -1):
            last_month = datetime.now() - relativedelta(months=i)
            text = format(last_month, '%B %Y')
            month_list.append(text)
        uid = request.session.uid
        employee = self.env['hr.employee'].sudo().search_read(
            [('user_id', '=', uid)], limit=1)
        for month in month_list:
            vals = {
                'l_month': month,
                'leave': 0
            }
            graph_result.append(vals)
        sql = """
                SELECT h.id, h.employee_id
                     , extract('month' FROM y)::int AS leave_month
                     , to_char(y, 'Month YYYY') as month_year
                     , GREATEST(y                    , h.date_from) AS date_from
                     , LEAST   (y + interval '1 month', h.date_to)   AS date_to
                FROM  (select * from hr_leave where state = 'validate') h
                     , generate_series(date_trunc('month', date_from::timestamp)
                                     , date_trunc('month', date_to::timestamp)
                                     , interval '1 month') y
                where date_trunc('month', GREATEST(y , h.date_from)) >= 
                date_trunc('month', now()) - interval '6 month' and
                date_trunc('month', GREATEST(y , h.date_from)) <= 
                date_trunc('month', now()) and h.employee_id = %s """
        self.env.cr.execute(sql, (employee[0]['id'],))
        results = self.env.cr.dictfetchall()
        for line in results:
            employee = self.browse(line['employee_id'])
            from_dt = fields.Datetime.from_string(line['date_from'])
            to_dt = fields.Datetime.from_string(line['date_to'])
            days = employee.get_work_days_dashboard(from_dt, to_dt)
            line['days'] = days
            vals = {
                'l_month': line['month_year'],
                'days': days
            }
            leave_lines.append(vals)
        if leave_lines:
            df = pd.DataFrame(leave_lines)
            rf = df.groupby(['l_month']).sum()
            result_lines = rf.to_dict('index')
            for line in result_lines:
                match = list(filter(
                    lambda d: d['l_month'].replace(' ', '') == line.replace(' ',
                                                                            ''),
                    graph_result))
                if match:
                    match[0]['leave'] = result_lines[line]['days']
        for result in graph_result:
            result['l_month'] = result['l_month'].split(' ')[:1][0].strip()[
                                :3] + " " + \
                                result['l_month'].split(' ')[1:2][0]
        return graph_result

    @api.model
    def join_resign_trends(self):
        """Generate trends related to employee joinings and resignations."""
        cr = self._cr
        month_list = []
        join_trend = []
        resign_trend = []
        for i in range(11, -1, -1):
            last_month = datetime.now() - relativedelta(months=i)
            text = format(last_month, '%B %Y')
            month_list.append(text)
        for month in month_list:
            vals = {
                'l_month': month,
                'count': 0
            }
            join_trend.append(vals)
        for month in month_list:
            vals = {
                'l_month': month,
                'count': 0
            }
            resign_trend.append(vals)
        cr.execute('''select to_char(create_date, 'Month YYYY') as l_month,
         count(id) from hr_employee
        WHERE create_date BETWEEN CURRENT_DATE - INTERVAL '12 months'
        AND CURRENT_DATE + interval '1 month - 1 day'
        group by l_month''')
        join_data = cr.fetchall()
        cr.execute('''select to_char(create_date, 'Month YYYY') as l_month,
         count(id) from hr_employee
        WHERE create_date BETWEEN CURRENT_DATE - INTERVAL '12 months'
        AND CURRENT_DATE + interval '1 month - 1 day'
        group by l_month;''')
        resign_data = cr.fetchall()
        for line in join_data:
            match = list(filter(
                lambda d: d['l_month'].replace(' ', '') == line[0].replace(' ',
                                                                           ''),
                join_trend))
            if match:
                match[0]['count'] = line[1]
        for line in resign_data:
            match = list(filter(
                lambda d: d['l_month'].replace(' ', '') == line[0].replace(' ',
                                                                           ''),
                resign_trend))
            if match:
                match[0]['count'] = line[1]
        for join in join_trend:
            join['l_month'] = join['l_month'].split(' ')[:1][0].strip()[:3]
        for resign in resign_trend:
            resign['l_month'] = resign['l_month'].split(' ')[:1][0].strip()[:3]
        graph_result = [{
            'name': 'Join',
            'values': join_trend
        }, {
            'name': 'Resign',
            'values': resign_trend
        }]
        return graph_result

    @api.model
    def get_attrition_rate(self):
        """
           Calculate the attrition rate for each month over the past year.
        """
        month_attrition = []
        monthly_join_resign = self.join_resign_trends()
        month_join = monthly_join_resign[0]['values']
        month_resign = monthly_join_resign[1]['values']
        sql = """
        SELECT (date_trunc('month', CURRENT_DATE))::date - interval '1' 
        month * s.a AS month_start
        FROM generate_series(0,11,1) AS s(a);"""
        self._cr.execute(sql)
        month_start_list = self._cr.fetchall()
        for month_date in month_start_list:
            self._cr.execute("""select count(id), 
            to_char(date '%s', 'Month YYYY') as l_month from hr_employee
            where create_date> date '%s' or create_date is null and 
            create_date < date '%s'
            """ % (month_date[0], month_date[0], month_date[0],))
            month_emp = self._cr.fetchone()
            match_join = \
                list(filter(
                    lambda d: d['l_month'] == month_emp[1].split(' ')[:1][
                                                  0].strip()[:3], month_join))[
                    0][
                    'count']
            match_resign = \
                list(filter(
                    lambda d: d['l_month'] == month_emp[1].split(' ')[:1][
                                                  0].strip()[:3],
                    month_resign))[0][
                    'count']
            month_avg = (month_emp[0] + match_join - match_resign + month_emp[
                0]) / 2
            attrition_rate = (match_resign / month_avg) * 100 \
                if month_avg != 0 else 0
            vals = {
                'month': month_emp[1].split(' ')[:1][0].strip()[:3],
                'attrition_rate': round(float(attrition_rate), 2)
            }
            month_attrition.append(vals)
        return month_attrition


class HrEmployeePublic(models.Model):
    """Inherit hr employee public for adding custom fields"""
    _inherit = 'hr.employee.public'

    birthday = fields.Date(string='Date of Birth', groups="base.group_user",
                           help="Birthday")