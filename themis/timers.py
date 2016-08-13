import themis.channel.event
import themis.codegen
import themis.cgen


def tick(millis: int, event: themis.channel.event.EventOutput) -> None:
    assert millis > 0
    nanos = millis * 1000000
    themis.codegen.add_init_call("start_timer_ns", themis.codegen.InitPhase.PHASE_BEGIN, nanos, event)


def ticker(millis: int, isolated=False) -> themis.channel.event.EventInput:
    assert millis > 0
    if not isolated:
        cached_tickers = themis.codegen.get_prop_init(ticker, lambda: {})
        if millis not in cached_tickers:
            cached_tickers[millis] = ticker(millis, isolated=True)
        return cached_tickers[millis]
    event_out, event_in = themis.channel.event.event_cell()
    tick(millis, event_out)
    return event_in


def _gen_proc_thread():
    themis.codegen.add_init_call("begin_timers", themis.codegen.InitPhase.PHASE_BEGIN)


def _ensure_proc_thread():
    themis.codegen.get_prop_init(_ensure_proc_thread, _gen_proc_thread)


def delay_ms(out: themis.channel.event.EventOutput, milliseconds: (int, float)) -> themis.channel.event.EventOutput:
    assert isinstance(milliseconds, (int, float))
    _ensure_proc_thread()
    nanos = int(milliseconds * 1000000)

    instant = themis.cgen.Instant(None)
    instant.transform("run_after_ns", None, nanos, out.get_ref())
    return themis.channel.EventOutput(instant)


def after_ms(begin: themis.channel.event.EventInput, milliseconds: (int, float)) -> themis.channel.event.EventInput:
    cell_out, cell_in = themis.channel.event.event_cell()
    begin.send(delay_ms(cell_out, milliseconds))
    return cell_in
