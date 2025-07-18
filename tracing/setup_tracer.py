from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor
)


def setup_tracer():
    # Create tracer provider
    provider = TracerProvider()

    # Create console exporter (we'll use Jaeger later)
    exporter = ConsoleSpanExporter()

    # Add processor to the provider
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Set the global tracer provider
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# Global tracer instance
tracer = setup_tracer()
