import wx
import time


class MyForm(wx.Frame):
    selfcall = False

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Timer Tutorial 1", size=(500, 500))

        # Add a panel so it looks the correct on all platforms
        self.panel = wx.Panel(self, wx.ID_ANY)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update, self.timer)

        hsizer = wx.BoxSizer(wx.VERTICAL)

        self.toggleBtn = wx.Button(self.panel, wx.ID_ANY, "Start")
        self.toggleBtn.Bind(wx.EVT_BUTTON, self.onToggle)

        self.cancelBtn = wx.Button(self.panel, wx.ID_ANY, "Cancel Self-call")
        self.cancelBtn.Bind(wx.EVT_BUTTON, self.onCancel)

        hsizer.Add(self.toggleBtn, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 15)
        hsizer.Add(self.cancelBtn, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 15)
        self.panel.SetSizer(hsizer)

    def onToggle(self, event):
        if self.timer.IsRunning():
            self.timer.Stop()
            self.selfcall = True
            self.on_timer()
            self.toggleBtn.SetLabel("Start")
            print("timer stopped!")
            # self.timer.Destroy() # use on closing
        else:
            print("starting timer...")
            self.timer.Start(1000)
            self.toggleBtn.SetLabel("Stop")
            self.selfcall = False

    def update(self, event):
        print("\nupdated: ", time.ctime())

    def onCancel(self, _):
        self.selfcall = False

    def on_timer(self):
        print('on_time called')
        if self.selfcall:
            print("self-calling CallLater timer")
            wx.CallLater(2000, self.on_timer)


# Run the program
if __name__ == "__main__":
    app = wx.App()
    frame = MyForm().Show()
    app.MainLoop()
