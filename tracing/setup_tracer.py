from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    BatchSpanProcessor,
    SimpleSpanProcessor
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # NEW


def setup_tracer():
    # Create resource with service name
    resource = Resource(attributes={
        SERVICE_NAME: "code-review-mas"
    })

    # Set up tracer provider
    provider = TracerProvider(resource=resource)

    # Console exporter (for debugging)
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(console_exporter))

    # Jaeger OTLP exporter (NEW)
    jaeger_exporter = OTLPSpanExporter(
        endpoint="localhost:4317",
        insecure=True
    )
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# Global tracer instance
tracer = setup_tracer()