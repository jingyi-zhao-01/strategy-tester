import logging
from random import randint

from flask import Flask, request
from opentelemetry import metrics, trace
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry providers
resource = Resource.create({"service.name": "dice-server"})
tp = TracerProvider(resource=resource)
tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(tp)

metric_exporter = ConsoleMetricExporter()
metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
mp = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(mp)

# Enable system metrics instrumentation (collects CPU, memory, etc.)
SystemMetricsInstrumentor().instrument()

tracer = trace.get_tracer("diceroller.tracer")
meter = metrics.get_meter("diceroller.meter")
# Now create a counter instrument to make measurements with
roll_counter = meter.create_counter(
    "dice.rolls",
    description="The number of rolls by roll value",
)


@app.route("/rolldice")
def roll_dice():
    # This creates a new span that's the child of the current one
    with tracer.start_as_current_span("roll") as roll_span:
        player = request.args.get("player", default=None, type=str)
        result = str(roll())
        roll_span.set_attribute("roll.value", result)
        # This adds 1 to the counter for the given roll value
        roll_counter.add(1, {"roll.value": result})
        if player:
            logger.warn("%s is rolling the dice: %s", player, result)
        else:
            logger.warn("Anonymous player is rolling the dice: %s", result)
        return result


def roll():
    return randint(1, 6)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
