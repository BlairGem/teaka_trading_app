"""Local-assets pages for the memory-only paper application."""
import math
from flask import render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from .database import db


def register_pages(app):
    @app.route('/')
    def index():
        return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('auth.login'))

    @login_required
    def workspace():
        return render_template('paper.html', section=request.endpoint,
                               data_root=app.config.get('PAPER_DATA_ROOT', 'Not configured'))

    for endpoint, path in [('dashboard', '/dashboard'), ('strategy_editor', '/strategy-editor'),
                           ('market_data', '/market-data'), ('backtesting', '/backtesting'), ('signals', '/signals')]:
        app.add_url_rule(path, endpoint, workspace)

    @app.route('/settings')
    @login_required
    def settings():
        return render_template('paper_account.html', section='settings')

    @app.route('/profile')
    @login_required
    def profile():
        return render_template('paper_account.html', section='profile')

    @login_required
    def unavailable():
        return jsonify(success=False, mode='paper', error='Broker connections and notifications unavailable in this paper session'), 503

    for endpoint in ['update_kucoin_api', 'update_ib_api', 'update_oanda_api', 'update_notification_settings']:
        app.add_url_rule('/' + endpoint, endpoint, unavailable, methods=['POST'])

    @app.route('/update_risk_settings', methods=['POST'])
    @login_required
    def update_risk_settings():
        try:
            values = {field: float(request.form[field]) for field in
                      ['max_position_size_pct', 'default_stop_loss_pct', 'default_take_profit_pct']}
            count = int(request.form['max_open_positions'])
            if not 0 <= count <= 100 or not all(math.isfinite(v) and 0 <= v < 100 for v in values.values()):
                raise ValueError('Invalid risk limits')
            if values['default_stop_loss_pct'] == 0 or values['default_take_profit_pct'] == 0:
                raise ValueError('Protective distances must be positive')
        except (ValueError, KeyError):
            return render_template('paper_account.html', section='settings', error='Enter finite limits: position 0–99.99%, positions 0–100, stop/take above 0 and below 100%.'), 400
        for field, value in values.items():
            setattr(current_user, field, value)
        current_user.max_open_positions = count
        db.session.commit()
        return render_template('paper_account.html', section='settings', message='Paper risk settings saved for this session.')

    @app.errorhandler(404)
    def missing(error):
        if request.path.startswith('/api/'):
            return jsonify(success=False, error='Owned resource not found', mode='paper'), 404
        return render_template('paper_account.html', section='error', error='Page not found'), 404
