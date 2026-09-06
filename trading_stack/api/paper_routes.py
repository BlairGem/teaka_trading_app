"""Authenticated paper APIs; no provider managers are imported here."""
import json
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from ..models import db, TradingStrategy, TradingSignal, TradeExecution, BacktestResult, PaperRun
from ..strategy_contracts import normalize_strategy_contract
from ..paper_runtime import positive, supported_pair


def serialize(row):
    result = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        result[column.name] = value.isoformat() if hasattr(value, 'isoformat') else value
    if isinstance(row, TradingStrategy):
        for name in ('trading_pairs', 'indicators_config', 'entry_conditions', 'exit_conditions'):
            result[name] = getattr(row, 'get_' + name)()
    return result


def init_app(app):
    bp = Blueprint('api', __name__, url_prefix='/api')

    def runtime():
        return current_app.extensions['paper_runtime']

    @bp.route('/paper/status')
    @login_required
    def paper_status():
        provider = runtime().provider
        return jsonify(mode='paper', state='simulated' if provider.clock is not None else 'unavailable',
                       data_origin=provider.data_origin, clock=provider.clock.isoformat() if provider.clock is not None else None,
                       timeframe=provider.timeframe, currency='USDT', memory_only=True,
                       fee_bps=runtime().config.fee_bps, slippage_bps=runtime().config.slippage_bps)

    @bp.errorhandler(ValueError)
    @bp.errorhandler(TypeError)
    @bp.errorhandler(KeyError)
    def invalid_input(error):
        db.session.rollback()
        return jsonify(success=False, mode='paper', error=str(error)), 400

    @bp.route('/account-balance')
    @login_required
    def balance():
        return jsonify(success=True, mode='paper', data=runtime().balance(current_user.id))

    @bp.route('/prices')
    @login_required
    def prices():
        provider = runtime().provider
        return jsonify(success=True, mode='paper', data_origin=provider.data_origin,
                       data=provider.get_latest_prices(list(provider.frames)))

    @bp.route('/chart-data')
    @login_required
    def chart():
        provider = runtime().provider
        frame = provider.get_historical_data(request.args.get('pair', 'BTC/USDT'), request.args.get('timeframe', '1h'), limit=int(request.args.get('limit', 100)))
        data = [dict(timestamp=t.isoformat(), **{k: float(v) for k, v in row.items()}) for t, row in frame.iterrows()]
        return jsonify(success=True, mode='paper', data_origin=provider.data_origin, data=data)

    @bp.route('/positions')
    @login_required
    def positions():
        return jsonify(success=True, mode='paper', data=runtime().positions(current_user.id))

    @bp.route('/positions/<position_id>/close', methods=['POST'])
    @login_required
    def close(position_id):
        result = runtime().close(current_user.id, position_id)
        return jsonify(result), 200 if result['success'] else 404

    @bp.route('/execute-trade', methods=['POST'])
    @login_required
    def execute():
        data = request.get_json()
        if data.get('mode', 'paper') != 'paper' or data.get('platform', 'paper') != 'paper':
            raise ValueError('Only paper execution is supported')
        result = runtime().manual_order(current_user.id, data['trading_pair'], data['order_type'], data['amount'])
        return jsonify(result), 200 if result['success'] else 400

    @bp.route('/trades')
    @login_required
    def trades():
        return jsonify([serialize(row) for row in TradeExecution.query.filter_by(user_id=current_user.id).order_by(TradeExecution.id.desc()).limit(100)])

    @bp.route('/signals')
    @login_required
    def signals():
        return jsonify([serialize(row) for row in TradingSignal.query.filter_by(user_id=current_user.id).order_by(TradingSignal.id.desc()).limit(100)])

    @bp.route('/signals/<int:signal_id>/execute', methods=['POST'])
    @login_required
    def execute_signal(signal_id):
        from ..trading_engine import execute_trade_from_signal
        signal = TradingSignal.query.filter_by(id=signal_id, user_id=current_user.id).first_or_404()
        data = request.get_json() or {}
        success = execute_trade_from_signal(signal, positive(data.get('amount', data.get('position_size'))), user_id=current_user.id)
        return jsonify(success=success, mode='paper'), 200 if success else 400

    def update_strategy_values(strategy, data):
        if data.get('use_ml_model') or data.get('ml_model_id'):
            raise ValueError('ML models are unavailable in paper mode')
        name = data.get('name', strategy.name)
        pairs = data.get('trading_pairs', strategy.get_trading_pairs())
        timeframe = data.get('timeframe', strategy.timeframe)
        if not isinstance(name, str) or not name.strip() or not pairs or not all(supported_pair(pair) for pair in pairs):
            raise ValueError('A name and USDT quoted trading pairs are required')
        if timeframe != runtime().provider.timeframe:
            raise ValueError('Strategy timeframe must match the local dataset')
        indicators = data.get('indicators_config', strategy.get_indicators_config())
        entries = data.get('entry_conditions', strategy.get_entry_conditions())
        exits = data.get('exit_conditions', strategy.get_exit_conditions())
        normalize_strategy_contract(indicators, entries)
        if exits:
            normalize_strategy_contract(indicators, [dict(rule, signal_type=rule.get('signal_type', rule.get('side', 'SELL'))) for rule in exits])
        for field, default in [('risk_per_trade_pct', 1.), ('stop_loss_pct', 2.), ('take_profit_pct', 4.)]:
            value = positive(data.get(field, getattr(strategy, field) or default))
            if value >= 100:
                raise ValueError('Risk percentages must be below 100')
            setattr(strategy, field, value)
        strategy.name, strategy.timeframe = name.strip(), timeframe
        strategy.description = data.get('description', strategy.description)
        strategy.is_active = bool(data.get('is_active', strategy.is_active))
        strategy.set_trading_pairs(pairs)
        strategy.set_indicators_config(indicators)
        strategy.set_entry_conditions(entries)
        strategy.set_exit_conditions(exits)

    @bp.route('/strategies', methods=['GET', 'POST'])
    @login_required
    def strategies():
        if request.method == 'GET':
            return jsonify([serialize(s) for s in TradingStrategy.query.filter_by(user_id=current_user.id).order_by(TradingStrategy.id)])
        strategy = TradingStrategy(user_id=current_user.id)
        update_strategy_values(strategy, request.get_json())
        db.session.add(strategy)
        db.session.commit()
        return jsonify(success=True, strategy_id=strategy.id, mode='paper')

    @bp.route('/strategies/<int:strategy_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def strategy(strategy_id):
        row = TradingStrategy.query.filter_by(id=strategy_id, user_id=current_user.id).first_or_404()
        if request.method == 'GET':
            return jsonify(serialize(row))
        if request.method == 'DELETE':
            # Preserve historical ownership and signal links; deactivate instead.
            row.is_active = False
        else:
            update_strategy_values(row, request.get_json())
        db.session.commit()
        return jsonify(success=True, mode='paper')

    @bp.route('/strategies/<int:strategy_id>/risk-metrics')
    @login_required
    def strategy_risk(strategy_id):
        row = TradingStrategy.query.filter_by(id=strategy_id, user_id=current_user.id).first_or_404()
        trades = TradeExecution.query.filter_by(strategy_id=row.id, user_id=current_user.id).all()
        return jsonify(mode='paper', data={'execution_count': len(trades), 'fees': sum(t.fee or 0 for t in trades)})

    @bp.route('/backtests/<int:backtest_id>')
    @login_required
    def backtest_result(backtest_id):
        return jsonify(serialize(BacktestResult.query.filter_by(id=backtest_id, user_id=current_user.id).first_or_404()))

    @bp.route('/backtests', methods=['GET', 'POST'])
    @login_required
    def backtest():
        if request.method == 'GET':
            return jsonify([serialize(row) for row in BacktestResult.query.filter_by(user_id=current_user.id).order_by(BacktestResult.id.desc())])
        from ..backtesting import run_backtest
        from ..paper_runtime import timestamp
        data = request.get_json()
        strategy = TradingStrategy.query.filter_by(id=data['strategy_id'], user_id=current_user.id).first_or_404()
        if strategy.use_ml_model:
            return unavailable()
        pair = data['trading_pair']
        if pair not in strategy.get_trading_pairs() or not supported_pair(pair):
            raise ValueError('Pair must belong to the owned strategy and use USDT')
        start, end = timestamp(data['start_date']), timestamp(data['end_date'])
        if end < start or runtime().provider.clock is None or end > runtime().provider.clock:
            raise ValueError('Backtest range must be within completed local candles')
        result_id = run_backtest(strategy.id, pair, start.to_pydatetime(), end.to_pydatetime(),
            positive(data.get('initial_balance', 10000)), market_provider=runtime().provider,
            strategy_lookup=lambda _: strategy, result_factory=BacktestResult, session=db.session,
            fee_bps=runtime().config.fee_bps, slippage_bps=runtime().config.slippage_bps)
        if result_id is None:
            db.session.rollback()
            raise ValueError('Backtest unavailable for these local data and strategy settings')
        return jsonify(success=True, mode='paper', backtest_id=result_id)

    @bp.route('/paper/runs')
    @login_required
    def runs():
        return jsonify([serialize(row) for row in PaperRun.query.filter_by(user_id=current_user.id).order_by(PaperRun.id.desc())])

    @bp.route('/paper/replay', methods=['POST'])
    @login_required
    def replay():
        from ..paper_replay import replay_csv, confined_path
        data = request.get_json()
        root = app.config.get('PAPER_DATA_ROOT')
        output_root = app.config.get('PAPER_OUTPUT_ROOT')
        if not root or not output_root:
            raise ValueError('Local replay roots have not been configured')
        source = confined_path(data['csv_path'], root, '.csv')
        output = confined_path(Path(output_root) / ('paper-run-' + uuid.uuid4().hex + '.json'), output_root, '.json')
        result = replay_csv(runtime(), current_user.id, source, data['trading_pair'], data['timeframe'],
                            data['start'], data['end'], data['data_origin'], output)
        return jsonify(result)

    @bp.route('/portfolio-risk')
    @bp.route('/position-exposure')
    @login_required
    def risk():
        held = runtime().positions(current_user.id)
        broker = runtime().account(current_user.id)
        return jsonify(mode='paper', equity=broker.equity(), cash=broker.cash,
                       exposure=sum(p['amount'] * p['current_price'] for p in held), currency='USDT')

    @login_required
    def unavailable(**kwargs):
        return jsonify(success=False, mode='paper', status='unavailable', error='This optional feature is inactive in the local paper runtime'), 503

    for index, path in enumerate(['/ml-models', '/ml-models/<int:model_id>', '/ml-models/<int:model_id>/predict',
        '/matlab-signal', '/futures/order', '/websocket', '/strategies/<int:strategy_id>/optimize',
        '/indicators', '/support-resistance', '/patterns', '/orderbook', '/market-trades',
        '/signals/manual', '/signals/<int:signal_id>/cancel']):
        bp.add_url_rule(path, f'unavailable_{index}', unavailable, methods=['GET', 'POST'])
    app.register_blueprint(bp)
