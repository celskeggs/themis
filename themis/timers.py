import themis.channel
import themis.exec.timers
import themis.codeinit
import themis.codegen


def tick(millis: int, event: themis.channel.EventOutput) -> None:
    assert millis > 0
    themis.codeinit.add_init_call(themis.codegen.ref(themis.exec.timers.start_timer), themis.codeinit.Phase.PHASE_BEGIN,
                                  args=(millis, event))


def ticker(millis: int, isolated=False) -> themis.channel.EventInput:
    assert millis > 0
    if not isolated:
        cached_tickers = themis.codegen.get_prop_init(ticker, lambda: {})
        if millis not in cached_tickers:
            cached_tickers[millis] = ticker(millis, isolated=True)
        return cached_tickers[millis]
    event = themis.channel.EventCell()
    tick(millis, event)
    return event
