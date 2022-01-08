import asyncio

import pytest

from wasp_general.api.onion import AOnionSessionProto, AOnionSessionFlowProto, WOnionSession, WOnionSequenceFlow
from wasp_general.api.onion import WOnionConditionalSequenceFlow


@pytest.mark.asyncio
async def test_abstract():
    pytest.raises(TypeError, AOnionSessionProto)
    with pytest.raises(NotImplementedError):
        await AOnionSessionProto.process(None, None)

    pytest.raises(TypeError, AOnionSessionFlowProto)
    with pytest.raises(NotImplementedError):
        await AOnionSessionFlowProto.next(None, None)


class TestWOnionSession:

    @pytest.mark.asyncio
    async def test(self):

        loop = asyncio.get_event_loop()
        future_result = loop.create_future()

        sf = WOnionSequenceFlow(
            lambda x: x + 1,
            lambda x: x + 2,
            lambda x: x + 3
        )

        onion = WOnionSession(sf)
        assert(isinstance(onion, WOnionSession) is True)
        assert(isinstance(onion, AOnionSessionProto) is True)

        result = await onion.process(3)
        assert(result == 9)

        result = await onion.process(10)
        assert(result == 16)

        sf = WOnionSequenceFlow(lambda x: future_result)
        onion = WOnionSession(sf)

        with pytest.raises(asyncio.exceptions.TimeoutError):
            await asyncio.wait_for(onion.process(1), 1)

        future_result = loop.create_future()
        future_result.set_result('pass')
        assert(await asyncio.wait_for(onion.process(1), 1) == 'pass')


class TestWOnionSequenceFlow:

    def test(self):
        sf = WOnionSequenceFlow()
        assert(isinstance(sf, WOnionSequenceFlow) is True)
        assert(isinstance(sf, AOnionSessionFlowProto) is True)
        pytest.raises(IndexError, sf.next, None)

        def foo(x):
            pass

        def bar(x):
            pass

        sf = WOnionSequenceFlow(foo, bar)
        next_fn, next_sf = sf.next(1)
        assert(next_fn is foo)
        assert(isinstance(next_sf, AOnionSessionFlowProto) is True)

        next_fn, next_sf = next_sf.next(1)
        assert(next_fn is bar)
        assert(next_sf is None)


class TestWOnionConditionalSequenceFlow:

    def test(self):
        sf = WOnionConditionalSequenceFlow()
        assert(isinstance(sf, WOnionConditionalSequenceFlow) is True)
        assert(isinstance(sf, AOnionSessionFlowProto) is True)
        pytest.raises(IndexError, sf.next, None)

        def foo(x):
            pass

        def bar(x):
            pass

        sf = WOnionConditionalSequenceFlow(
            WOnionConditionalSequenceFlow.Comparator(
                compare_fn=lambda x: x > 5,
                on_true=WOnionSequenceFlow(foo),
                on_false=WOnionSequenceFlow(bar)
            )
        )
        next_fn, next_sf = sf.next(1)
        assert(next_fn is None)
        assert(next_sf is not None)
        assert(next_sf.next(1)[0] is bar)

        sf = WOnionConditionalSequenceFlow(
            WOnionConditionalSequenceFlow.Comparator(
                compare_fn=lambda x: x < 5,
                on_false=WOnionSequenceFlow(bar)
            ),
            WOnionConditionalSequenceFlow.Comparator(
                compare_fn=lambda x: x == 1,
                on_true=WOnionSequenceFlow(foo),
            ),
        )
        _, next_sf = sf.next(1)
        assert(next_sf.next(1)[0] is foo)

        pytest.raises(IndexError, sf.next, 2)

        sf = WOnionConditionalSequenceFlow(
            WOnionConditionalSequenceFlow.Comparator(
                compare_fn=lambda x: x < 5,
                on_false=WOnionSequenceFlow(bar)
            ),
            WOnionConditionalSequenceFlow.Comparator(
                compare_fn=lambda x: x == 1,
                on_true=WOnionSequenceFlow(bar),
            ),
            default_flow=WOnionSequenceFlow(foo)
        )
        _, next_sf = sf.next(2)
        assert(next_sf.next(1)[0] is foo)
