"""stockroom — in-memory inventory with time-limited reservations.

A hold sets quantity aside without removing it from the on-hand count;
available stock is on-hand minus active holds.  A hold ends one of three
ways: committed (the quantity permanently leaves stock), released (the
quantity returns to the available pool), or expired by the sweeper once
its ttl has elapsed.
"""
import itertools
import time

DEFAULT_TTL = 900  # hold lifetime in seconds


class InsufficientStock(Exception):
    pass


def _now_ms():
    return int(time.time() * 1000)


class Hold:
    _ids = itertools.count(1)

    def __init__(self, sku, qty, ttl):
        self.id = next(Hold._ids)
        self.sku = sku
        self.qty = qty
        self.state = "active"
        self.expires_at = _now_ms() + ttl

    def __repr__(self):
        return f"<Hold {self.id} {self.sku} x{self.qty} {self.state}>"


class StockRoom:
    """Tracks on-hand stock and the holds placed on it, per SKU."""

    def __init__(self):
        self._on_hand = {}
        self._reserved = {}
        self._holds = {}

    def add_stock(self, sku, qty):
        if qty <= 0:
            raise ValueError("qty must be positive")
        self._on_hand[sku] = self._on_hand.get(sku, 0) + qty

    def on_hand(self, sku):
        return self._on_hand.get(sku, 0)

    def available(self, sku):
        return self._on_hand.get(sku, 0) - self._reserved.get(sku, 0)

    def get_hold(self, hold_id):
        return self._holds.get(hold_id)

    def reserve(self, sku, qty, ttl=DEFAULT_TTL):
        """Place a hold on ``qty`` of ``sku`` for ``ttl`` seconds.

        Returns the hold id; raises InsufficientStock when the available
        pool is smaller than the request.
        """
        if qty <= 0:
            raise ValueError("qty must be positive")
        if self.available(sku) < qty:
            raise InsufficientStock(
                f"{sku}: requested {qty}, available {self.available(sku)}")
        self._reserved[sku] = self._reserved.get(sku, 0) + qty
        hold = Hold(sku, qty, ttl)
        self._holds[hold.id] = hold
        return hold.id

    def commit(self, hold_id):
        """Consume a hold: its quantity permanently leaves on-hand stock."""
        hold = self._holds.get(hold_id)
        if hold is None or hold.state != "active":
            return False
        self._reserved[hold.sku] -= hold.qty
        self._on_hand[hold.sku] -= hold.qty
        hold.state = "committed"
        return True

    def release(self, hold_id):
        """Give a hold's quantity back to the available pool."""
        hold = self._holds.get(hold_id)
        if hold is None:
            return False
        self._reserved[hold.sku] -= hold.qty
        hold.state = "released"
        return True

    def expire_stale(self):
        """Sweep holds whose ttl has elapsed; returns the count expired."""
        now = _now_ms()
        count = 0
        for hold in self._holds.values():
            if hold.state == "active" and now >= hold.expires_at:
                self._reserved[hold.sku] -= hold.qty
                hold.state = "expired"
                count += 1
        return count


def _demo():
    room = StockRoom()
    room.add_stock("widget", 10)
    h1 = room.reserve("widget", 4)
    assert room.available("widget") == 6
    h2 = room.reserve("widget", 3, ttl=3600)
    assert room.available("widget") == 3
    assert room.commit(h1)
    assert room.on_hand("widget") == 6
    assert room.available("widget") == 3
    assert room.release(h2)
    assert room.available("widget") == 6
    assert not room.commit(h1)
    assert room.expire_stale() == 0
    try:
        room.reserve("widget", 7)
    except InsufficientStock:
        pass
    else:
        raise AssertionError("expected InsufficientStock")
    assert room.get_hold(h1).state == "committed"
    print("OK")


if __name__ == "__main__":
    _demo()
