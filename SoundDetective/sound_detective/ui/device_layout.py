"""Shared compact chrome: the instrument keeps the space, actions share a row."""

def compact_workspace(owner,actions,rows=()):
    root=owner.centralWidget();layout=root.layout()
    layout.setContentsMargins(10,8,10,6);layout.setSpacing(4)
    root.setStyleSheet('QPushButton {font-size:12px;padding:4px 7px;min-height:18px;} '
        'QGroupBox {font-size:12px;} QTabBar::tab {font-size:12px;padding:5px 9px;}')
    bar=owner.edit_bar
    if bar.parentWidget() and bar.parentWidget().layout():bar.parentWidget().layout().removeWidget(bar)
    for row in rows:
        layout.removeItem(row)
        while row.count():
            item=row.takeAt(0)
            if item.widget() and item.widget() not in actions and item.widget() is not bar:item.widget().hide()
    bar.append_actions(actions)
    layout.removeWidget(bar)
    # Keep the compact edit/submit row above the final status line.
    status=getattr(owner,'status',None)
    if status is not None:layout.addWidget(status)
    index=next((i for i in range(layout.count()) if layout.itemAt(i).widget() is status),layout.count())
    layout.insertWidget(index,bar)
    bar.show()
    for name in ('title','rules','stage_label','stage_banner','locked','feedback'):
        widget=getattr(owner,name,None)
        if widget is not None:widget.setStyleSheet('font-size:12px;')
    score=getattr(owner,'score',None)
    if score is not None:score.setStyleSheet('font-size:15px;color:#efd6a0;')
    if status is not None:status.setStyleSheet('font-size:11px;');status.setMaximumHeight(24)
    for name in ('target_group','notebook','clue_group'):
        widget=getattr(owner,name,None)
        if widget is not None:widget.setMaximumWidth(275)


def help_caption(button,language,tier=None):
    zh=language=='zh-Hant'
    label='幫助／設備引導' if zh else 'Help / guidance'
    if tier is not None:label+=f' · {tier}/3'
    button.setText(label)
    button.setMaximumHeight(30)
    button.setToolTip('取得下一層提示，並前往相應設備或標出控制；不改答案，也不增加提交次數。' if zh else
        'Get the next clue and open its device or highlight the control. Your answer and submission count stay unchanged.')
