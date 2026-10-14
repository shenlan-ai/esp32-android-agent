## Decisions
从当前已核验的两个原速MP4留存本地副本并校验原SHA256，再按setpts=(PTS-STARTPTS)/5加速，30fps/H.264/yuv420p/fast-start、无音频，分辨率和画面内容不变。替换现有仓库MP4路径，只缩短播放时间、不剪切新的时间区段。记录输出时长、字节数、SHA256及与原时长/5的误差。抽帧核对开头、过程和结尾，完整解码。

GitHub编辑草稿上传两段新MP4取得实际附件URL，更新README及媒体README并核验原生播放器实际时长和播放；不发布issue/comment。README明确5倍速，录像播放时长不能当作真实任务耗时。闹钟保留两段拼接及间隔未录制说明，源录制时长/原hash留作历史来源，不冒充当前5x文件属性。截图不变。

## Validation
严格校验OpenSpec；MP4完整解码、尺寸/编码/fast-start、时长比例、抽帧与SHA256；本地Markdown链接、说明和附件一致；git diff --check和check_changes.py；记录限制后归档并复核正式规格。
