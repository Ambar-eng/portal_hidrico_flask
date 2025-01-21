from azure.monitor.opentelemetry import configure_azure_monitor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry import trace
import os

class AzureMonitor:
    def __init__(self, app, connection_string):
        self.app = app
        self.connection_string = connection_string

    def start(self):
        resource = Resource(attributes={"service.name": "Application Dashboard Template"})
        provider = TracerProvider(resource=resource)
        span_processor = BatchSpanProcessor(AzureMonitorTraceExporter.from_connection_string(self.connection_string))
        provider.add_span_processor(span_processor)
        trace.set_tracer_provider(provider)

        FlaskInstrumentor().instrument_app(self.app)
        RequestsInstrumentor().instrument()

        print("Azure Monitor configuration complete.")
