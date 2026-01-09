"""Unit tests for Clock abstraction."""
from ntag424_sdm_provisioner.tui.clock import FakeClock, RealClock


def test_fake_clock_advance():
    """Test FakeClock time advancement."""
    clock = FakeClock()
    assert clock.current_time == 0.0
    
    clock.advance(5.0)
    assert clock.current_time == 5.0
    
    clock.advance(10.0)
    assert clock.current_time == 15.0


def test_fake_clock_schedule():
    """Test FakeClock scheduled callbacks."""
    clock = FakeClock()
    results = []
    
    # Schedule callbacks
    clock.schedule(5.0, lambda: results.append('5s'))
    clock.schedule(10.0, lambda: results.append('10s'))
    clock.schedule(3.0, lambda: results.append('3s'))
    
    # No callbacks triggered yet
    assert results == []
    
    # Advance to 3s - triggers first callback
    clock.advance(3.0)
    assert results == ['3s']
    
    # Advance to 5s - triggers second callback
    clock.advance(2.0)
    assert results == ['3s', '5s']
    
    # Advance to 10s - triggers third callback
    clock.advance(5.0)
    assert results == ['3s', '5s', '10s']


def test_fake_clock_sleep():
    """Test FakeClock sleep advances time."""
    clock = FakeClock()
    clock.sleep(7.5)
    assert clock.current_time == 7.5


def test_real_clock_exists():
    """Smoke test: RealClock can be instantiated."""
    clock = RealClock()
    assert clock is not None
