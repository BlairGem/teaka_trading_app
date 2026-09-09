from __future__ import annotations

import json
import math
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

Side = Literal["BUY", "SELL"]
OrderStatus = Literal["FILLED", "REJECTED"]


@dataclass(frozen=True)
class PaperConfig:
    initial_cash: float = 10_000.0
    max_order_notional: float = 1_000.0
    max_position_pct: float = 0.20
    max_drawdown_pct: float = 0.15
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    allow_shorting: bool = False
    allowed_symbols: tuple[str, ...] = ("BTC-USDT", "ETH-USDT", "SOL-USDT")


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    average_cost: float = 0.0
    realized_pnl: float = 0.0


@dataclass(frozen=True)
class Fill:
    order_id: str
    timestamp: str
    symbol: str
    side: Side
    quantity: float
    requested_price: float
    fill_price: float
    notional: float
    fee: float
    strategy: str
    status: OrderStatus
    reason: str = ""


def _validate_config(config: PaperConfig) -> None:
    positive_fields = ("initial_cash", "max_order_notional")
    for field in positive_fields:
        value = getattr(config, field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{field} must be a positive finite number")

    percentage_fields = ("max_position_pct", "max_drawdown_pct")
    for field in percentage_fields:
        value = getattr(config, field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 < value <= 1
        ):
            raise ValueError(f"{field} must be a finite number in (0, 1]")

    for field in ("fee_bps", "slippage_bps"):
        value = getattr(config, field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value < 10_000
        ):
            raise ValueError(f"{field} must be a finite number in [0, 10000)")

    if (
        not isinstance(config.allowed_symbols, tuple)
        or not config.allowed_symbols
        or any(
            not isinstance(symbol, str) or not symbol.strip()
            for symbol in config.allowed_symbols
        )
    ):
        raise ValueError("allowed_symbols must be a non-empty tuple of non-blank strings")

    if config.allow_shorting is not False:
        raise ValueError("allow_shorting=True is not supported by the paper broker")


class PaperBroker:
    """Paper-only broker with no exchange SDK imports or network order routes."""

    def __init__(self, config: PaperConfig, log_path: Optional[Path] = None, clock=None) -> None:
        _validate_config(config)
        self.config = config
        self.clock = clock
        self.cash = float(config.initial_cash)
        self.positions: Dict[str, Position] = {}
        self.last_prices: Dict[str, float] = {}
        self.fills: List[Fill] = []
        self.high_water_mark = float(config.initial_cash)
        self.kill_switch = False
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return self.clock() if self.clock is not None else datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _valid_number(value: float) -> bool:
        return isinstance(value, (int, float)) and math.isfinite(value) and value > 0

    def mark(self, symbol: str, price: float) -> dict:
        if not self._valid_number(price):
            raise ValueError("mark price must be a positive finite number")
        self.last_prices[symbol] = float(price)
        equity = self.equity()
        self.high_water_mark = max(self.high_water_mark, equity)
        drawdown = self.drawdown_pct()
        if drawdown >= self.config.max_drawdown_pct:
            self.kill_switch = True
        return {
            "symbol": symbol,
            "price": float(price),
            "equity": equity,
            "drawdown_pct": drawdown,
            "kill_switch": self.kill_switch,
        }

    def equity(self) -> float:
        market_value = 0.0
        for symbol, position in self.positions.items():
            price = self.last_prices.get(symbol, position.average_cost)
            market_value += position.quantity * price
        return self.cash + market_value

    def drawdown_pct(self) -> float:
        if self.high_water_mark <= 0:
            return 0.0
        return max(0.0, (self.high_water_mark - self.equity()) / self.high_water_mark)

    def _reject(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        mark_price: float,
        strategy: str,
        reason: str,
    ) -> Fill:
        fill = Fill(
            order_id=str(uuid.uuid4()),
            timestamp=self._now(),
            symbol=symbol,
            side=side,
            quantity=float(quantity),
            requested_price=float(mark_price),
            fill_price=float(mark_price),
            notional=float(quantity) * float(mark_price),
            fee=0.0,
            strategy=strategy,
            status="REJECTED",
            reason=reason,
        )
        self._record(fill)
        return fill

    def submit_market_order(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        mark_price: float,
        strategy: str = "manual",
    ) -> Fill:
        side = side.upper()  # type: ignore[assignment]
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        if not self._valid_number(quantity) or not self._valid_number(mark_price):
            raise ValueError("quantity and mark_price must be positive finite numbers")
        if symbol not in self.config.allowed_symbols:
            return self._reject(symbol, side, quantity, mark_price, strategy, "symbol_not_allowed")

        self.mark(symbol, mark_price)
        if self.kill_switch and side == "BUY":
            return self._reject(symbol, side, quantity, mark_price, strategy, "kill_switch_active")

        slip = self.config.slippage_bps / 10_000.0
        fill_price = mark_price * (1 + slip if side == "BUY" else 1 - slip)
        notional = quantity * fill_price
        fee = notional * self.config.fee_bps / 10_000.0

        position = self.positions.get(symbol)
        if side == "SELL" and (position is None or quantity > position.quantity + 1e-9):
            return self._reject(symbol, side, quantity, mark_price, strategy, "shorting_disabled")
        if side == "BUY" and notional > self.config.max_order_notional + 1e-9:
            return self._reject(symbol, side, quantity, mark_price, strategy, "max_order_notional")

        equity_before = self.equity()

        if side == "BUY":
            if position is None:
                position = Position(symbol=symbol)
                self.positions[symbol] = position
            if self.cash + 1e-9 < notional + fee:
                return self._reject(
                    symbol, side, quantity, mark_price, strategy, "insufficient_virtual_cash"
                )
            projected_qty = position.quantity + quantity
            projected_value = projected_qty * fill_price
            if projected_value > equity_before * self.config.max_position_pct + 1e-9:
                return self._reject(symbol, side, quantity, mark_price, strategy, "max_position_pct")
            total_cost = position.quantity * position.average_cost + notional + fee
            position.quantity = projected_qty
            position.average_cost = total_cost / projected_qty
            self.cash -= notional + fee
        else:
            assert position is not None
            position.realized_pnl += quantity * (fill_price - position.average_cost) - fee
            position.quantity -= quantity
            self.cash += notional - fee
            if abs(position.quantity) < 1e-12:
                position.quantity = 0.0
                position.average_cost = 0.0

        fill = Fill(
            order_id=str(uuid.uuid4()),
            timestamp=self._now(),
            symbol=symbol,
            side=side,
            quantity=float(quantity),
            requested_price=float(mark_price),
            fill_price=float(fill_price),
            notional=float(notional),
            fee=float(fee),
            strategy=strategy,
            status="FILLED",
        )
        self._record(fill)
        self.mark(symbol, mark_price)
        return fill

    def _record(self, fill: Fill) -> None:
        self.fills.append(fill)
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(fill), sort_keys=True) + "\n")

    def snapshot(self) -> dict:
        return {
            "mode": "paper",
            "live_order_routes": False,
            "cash": round(self.cash, 8),
            "equity": round(self.equity(), 8),
            "high_water_mark": round(self.high_water_mark, 8),
            "drawdown_pct": round(self.drawdown_pct(), 8),
            "kill_switch": self.kill_switch,
            "positions": {key: asdict(value) for key, value in self.positions.items()},
            "fill_count": len(self.fills),
        }


def load_config(path: Path) -> PaperConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if "allowed_symbols" in raw:
        if not isinstance(raw["allowed_symbols"], list):
            raise ValueError("allowed_symbols must be a JSON array")
        raw["allowed_symbols"] = tuple(raw["allowed_symbols"])
    config = PaperConfig(**raw)
    _validate_config(config)
    return config
