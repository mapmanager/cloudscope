"""Runtime MVC/event-bus telemetry for CloudScope development diagnostics.

This module is intentionally passive and safe to import from core code. Telemetry is
inactive unless ``CLOUDSCOPE_ENABLE_MVC_TELEMETRY`` is set to a true value.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Any

_TRUE_VALUES = {'1', 'true', 'yes', 'y', 'on'}
_MAX_RECENT_EVENTS = 200


def is_mvc_telemetry_enabled() -> bool:
    """Return whether MVC telemetry should collect runtime data."""
    return os.getenv('CLOUDSCOPE_ENABLE_MVC_TELEMETRY', '').strip().lower() in _TRUE_VALUES


@dataclass(slots=True)
class FlowRecord:
    """One recent event-handler delivery record."""

    timestamp: float
    event_name: str
    event_kind: str
    handler_name: str
    handler_role: str
    sender_name: str | None
    sender_role: str | None
    status: str
    error: str | None = None


class MVCTelemetry:
    """Collect event-bus publish/subscribe traffic for dev visualization."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._subscriptions: dict[str, set[str]] = defaultdict(set)
        self._nodes: dict[str, str] = {}
        self._links: dict[str, dict[str, Any]] = {}
        self._recent: deque[FlowRecord] = deque(maxlen=_MAX_RECENT_EVENTS)
        self._publish_counts: dict[str, int] = defaultdict(int)
        self._handler_errors: dict[str, int] = defaultdict(int)

    def clear(self) -> None:
        """Clear collected runtime telemetry."""
        with self._lock:
            self._subscriptions.clear()
            self._nodes.clear()
            self._links.clear()
            self._recent.clear()
            self._publish_counts.clear()
            self._handler_errors.clear()

    def record_subscription(self, event_type: type, handler: Callable[[Any], None]) -> None:
        """Record that a handler is subscribed to an event type."""
        if not is_mvc_telemetry_enabled():
            return
        event_name = self._event_type_name(event_type)
        handler_name = self._handler_name(handler)
        handler_role = self._handler_role(handler)
        with self._lock:
            self._subscriptions[event_name].add(handler_name)
            self._nodes[event_name] = self._event_kind_from_type(event_type)
            self._nodes[handler_name] = handler_role
            self._ensure_link(event_name, handler_name, 'subscribed', 0, status='subscribed')

    def record_delivery_start(
        self,
        event: object,
        handler: Callable[[Any], None],
        *,
        sender: object | None = None,
    ) -> None:
        """Record that an event is about to be delivered to a handler."""
        if not is_mvc_telemetry_enabled():
            return
        self._record_delivery(event, handler, sender=sender, status='ok', error=None)

    def record_delivery_error(
        self,
        event: object,
        handler: Callable[[Any], None],
        error: BaseException,
        *,
        sender: object | None = None,
    ) -> None:
        """Record that a handler raised while processing an event."""
        if not is_mvc_telemetry_enabled():
            return
        self._record_delivery(event, handler, sender=sender, status='error', error=f'{type(error).__name__}: {error}')

    def build_echart_options(self) -> dict[str, Any]:
        """Return Apache ECharts options for the current telemetry graph."""
        with self._lock:
            nodes = [self._echart_node(name, role) for name, role in sorted(self._nodes.items())]
            links = list(self._links.values())

        return {
            'title': {
                'text': 'CloudScope MVC Event Flow',
                'left': 'center',
                'textStyle': {'fontSize': 14},
            },
            'tooltip': {
                'trigger': 'item',
                'formatter': '{b}',
            },
            'legend': {
                'top': 28,
                'data': ['intent', 'state', 'handler', 'view', 'controller', 'task', 'system', 'unknown'],
            },
            'series': [{
                'type': 'graph',
                'layout': 'force',
                'categories': [
                    {'name': 'intent'},
                    {'name': 'state'},
                    {'name': 'handler'},
                    {'name': 'view'},
                    {'name': 'controller'},
                    {'name': 'task'},
                    {'name': 'system'},
                    {'name': 'unknown'},
                ],
                'force': {'repulsion': 520, 'edgeLength': 170, 'gravity': 0.08},
                'roam': True,
                'draggable': True,
                'edgeSymbol': ['none', 'arrow'],
                'edgeSymbolSize': [4, 8],
                'label': {'show': True, 'position': 'bottom', 'fontSize': 10},
                'edgeLabel': {'show': True, 'fontSize': 9},
                'data': nodes,
                'links': links,
                'lineStyle': {'opacity': 0.75, 'curveness': 0.16},
            }],
        }

    def summary(self) -> dict[str, int]:
        """Return compact counts for display in the diagnostics view."""
        with self._lock:
            return {
                'events': len(self._publish_counts),
                'handlers': sum(len(handlers) for handlers in self._subscriptions.values()),
                'edges': len(self._links),
                'deliveries': sum(self._publish_counts.values()),
                'errors': sum(self._handler_errors.values()),
            }

    def recent_records(self) -> list[FlowRecord]:
        """Return recent delivery records, newest first."""
        with self._lock:
            return list(reversed(self._recent))

    def _record_delivery(
        self,
        event: object,
        handler: Callable[[Any], None],
        *,
        sender: object | None,
        status: str,
        error: str | None,
    ) -> None:
        event_name = event.__class__.__name__
        event_kind = self._event_kind(event)
        handler_name = self._handler_name(handler)
        handler_role = self._handler_role(handler)
        sender_name = sender.__class__.__name__ if sender is not None else None
        sender_role = self._object_role(sender) if sender is not None else None

        with self._lock:
            self._nodes[event_name] = event_kind
            self._nodes[handler_name] = handler_role
            if sender_name is not None and sender_role is not None:
                self._nodes[sender_name] = sender_role
                self._increment_link(sender_name, event_name, 'published', status=status)
            self._increment_link(event_name, handler_name, status, status=status)
            self._publish_counts[event_name] += 1
            if status == 'error':
                self._handler_errors[handler_name] += 1
            self._recent.append(FlowRecord(
                timestamp=time.time(),
                event_name=event_name,
                event_kind=event_kind,
                handler_name=handler_name,
                handler_role=handler_role,
                sender_name=sender_name,
                sender_role=sender_role,
                status=status,
                error=error,
            ))

    def _ensure_link(self, source: str, target: str, label: str, count: int, *, status: str) -> dict[str, Any]:
        key = f'{source}->{target}:{label}'
        link = self._links.get(key)
        if link is None:
            link = {
                'source': source,
                'target': target,
                'value': label,
                'count': count,
                'status': status,
                'label': {'show': True, 'formatter': label, 'fontSize': 9},
                'lineStyle': {'width': 1 if count == 0 else 2, 'opacity': 0.35 if count == 0 else 0.8},
            }
            self._links[key] = link
        return link

    def _increment_link(self, source: str, target: str, label: str, *, status: str) -> None:
        link = self._ensure_link(source, target, label, 0, status=status)
        link['count'] += 1
        link['status'] = status
        count = int(link['count'])
        link['lineStyle']['width'] = min(1 + count, 9)
        link['lineStyle']['opacity'] = 0.9
        if status == 'error':
            link['lineStyle']['color'] = '#d9534f'

    def _echart_node(self, name: str, role: str) -> dict[str, Any]:
        category_index = {
            'intent': 0,
            'state': 1,
            'handler': 2,
            'view': 3,
            'controller': 4,
            'task': 5,
            'system': 6,
            'unknown': 7,
        }.get(role, 7)
        size = {
            'intent': 36,
            'state': 36,
            'controller': 50,
            'view': 44,
            'task': 42,
            'system': 38,
            'handler': 34,
            'unknown': 30,
        }.get(role, 30)
        return {
            'name': name,
            'category': category_index,
            'symbolSize': size,
            'value': role,
            'label': {'show': True, 'position': 'bottom', 'fontSize': 10},
        }

    def _event_type_name(self, event_type: type) -> str:
        return getattr(event_type, '__name__', str(event_type))

    def _event_kind_from_type(self, event_type: type) -> str:
        names = {cls.__name__ for cls in getattr(event_type, '__mro__', ())}
        if 'IntentEvent' in names:
            return 'intent'
        if 'StateEvent' in names:
            return 'state'
        return 'unknown'

    def _event_kind(self, event: object) -> str:
        return self._event_kind_from_type(event.__class__)

    def _handler_name(self, handler: Callable[[Any], None]) -> str:
        owner = getattr(handler, '__self__', None)
        method_name = getattr(handler, '__name__', None)
        if owner is not None and method_name:
            return f'{owner.__class__.__name__}.{method_name}'
        qualname = getattr(handler, '__qualname__', None)
        if qualname:
            return qualname
        return repr(handler)

    def _handler_role(self, handler: Callable[[Any], None]) -> str:
        owner = getattr(handler, '__self__', None)
        if owner is not None:
            return self._object_role(owner)
        return 'handler'

    def _object_role(self, obj: object | None) -> str:
        if obj is None:
            return 'unknown'
        explicit = getattr(obj, '_telemetry_role', None)
        if isinstance(explicit, str) and explicit:
            return explicit
        cls_name = obj.__class__.__name__
        module = getattr(obj.__class__, '__module__', '')
        if cls_name.endswith('Controller') or '.controllers.' in module:
            return 'controller'
        if cls_name.endswith('View') or '.views.' in module:
            return 'view'
        if 'TaskRunner' in cls_name:
            return 'task'
        if module.startswith('cloudscope.'):
            return 'system'
        return 'unknown'


mvc_telemetry = MVCTelemetry()
