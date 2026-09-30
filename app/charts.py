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

	class options:
		legend = Options.Legend(display=False)

class SentimentChart(JournalBaseChart):
	type = ChartType.Line

class SentimentByMonthChart(JournalBaseChart):
	type = ChartType.Bar

	class options:
		legend = Options.Legend(display=False)
		_yAxes = [Options.General(ticks=Options.General(suggestedMin=0, suggestedMax=0.1))]
		scales = Options.General(yAxes=_yAxes)

class NameChart(JournalBaseChart):
	type = ChartType.Line

	class options:
		# Unlike the other charts, this one draws multiple differently-colored
		# lines (one per name), so the legend is needed to tell them apart.
		legend = Options.Legend(display=True)

class NameTimelineChart(JournalBaseChart):
	type = ChartType.Bar

	class options:
		# Each bar is a stack of one segment per name, so the legend distinguishes
		# names and both axes need "stacked" set for Chart.js to stack instead of
		# grouping the segments side by side.
		legend = Options.Legend(display=True)
		_xAxes = [Options.General(stacked=True)]
		_yAxes = [Options.General(stacked=True)]
		scales = Options.General(xAxes=_xAxes, yAxes=_yAxes)