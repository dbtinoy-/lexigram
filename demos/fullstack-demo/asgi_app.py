from lexigram.app import Application

from shorts_creator.main import RootModule

app = Application(name="shorts-creator")
app.add_modules([RootModule.configure()])
