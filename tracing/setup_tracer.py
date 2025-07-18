from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor
)


def setup_tracer():
    # Tracer provider
    provider = TracerProvider()

    # Console exporter (we'll use Jaeger later)
    exporter = ConsoleSpanExporter()

    # Add processor to the provider
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # The global tracer provider
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# Global tracer instance
tracer = setup_tracer()
