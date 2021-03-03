from pychartjs import BaseChart, ChartType, Color, Options

class JournalBaseChart(BaseChart):
	class options:
		legend = Options.Legend(display=False)

	class data:
		backgroundColor = Color.RGBA(211, 200, 217, 1)

class WordChart(JournalBaseChart):
	type = ChartType.Bar

class NGramChart(JournalBaseChart):
	type = ChartType.HorizontalBar

class SentimentChart(JournalBaseChart):
	type = ChartType.Line

class SentimentByMonthChart(JournalBaseChart):
	type = ChartType.Bar

	class options:
		legend = Options.Legend(display=False)
		_yAxes = [Options.General(ticks=Options.General(suggestedMin=0, suggestedMax=0.1))]
		scales = Options.General(yAxes=_yAxes)
