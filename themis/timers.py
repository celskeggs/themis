import themisexec.timers

import themis.channel.event
import themis.codegen
import themis.pygen


def tick(millis: int, event: themis.channel.event.EventOutput) -> None:
    assert millis > 0
    themis.codegen.add_init_call(themisexec.timers.start_timer, themis.codegen.InitPhase.PHASE_BEGIN, millis, event)


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
    themis.codegen.add_init_call(themisexec.timers.start_proc_thread, themis.codegen.InitPhase.PHASE_BEGIN)


def _ensure_proc_thread():
    themis.codegen.get_prop_init(_ensure_proc_thread, _gen_proc_thread)


def delay_ms(out: themis.channel.event.EventOutput, milliseconds: (int, float)) -> themis.channel.event.EventOutput:
    assert isinstance(milliseconds, (int, float))
    _ensure_proc_thread()
    seconds = milliseconds / 1000.0

    instant = themis.pygen.Instant(None)
    instant.transform(themisexec.timers.run_after, None, seconds, out.get_ref())
    return themis.channel.EventOutput(instant)


def after_ms(begin: themis.channel.event.EventInput, milliseconds: (int, float)) -> themis.channel.event.EventInput:
    cell_out, cell_in = themis.channel.event.event_cell()
    begin.send(delay_ms(cell_out, milliseconds))
    return cell_in
