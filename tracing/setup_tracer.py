from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    BatchSpanProcessor  # NEW
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


def setup_tracer():
    # Tracer provider with service name
    resource = Resource(attributes={
        SERVICE_NAME: "code-review-mas"
    })
    provider = TracerProvider(resource=resource)

    # Console exporter
    console_exporter = ConsoleSpanExporter()

    # Use BatchSpanProcessor for better performance
    processor = BatchSpanProcessor(
        console_exporter,
        max_export_batch_size=100,
        schedule_delay_millis=5000
    )
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)


# Global tracer instance
tracer = setup_tracer()