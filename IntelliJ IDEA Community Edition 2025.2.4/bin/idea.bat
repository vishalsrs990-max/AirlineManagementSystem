@ECHO OFF

::----------------------------------------------------------------------
:: IntelliJ IDEA startup script.
::----------------------------------------------------------------------

:: ---------------------------------------------------------------------
:: Ensure IDE_HOME points to the directory where the IDE is installed.
:: ---------------------------------------------------------------------
SET "IDE_BIN_DIR=%~dp0"
PUSHD %IDE_BIN_DIR%
SET "IDE_BIN_DIR=%CD%"
POPD
FOR /F "delims=" %%i in ("%IDE_BIN_DIR%\..") DO SET "IDE_HOME=%%~fi"

:: ---------------------------------------------------------------------
:: Locate a JRE installation directory which will be used to run the IDE.
:: Try (in order): IDEA_JDK, idea64.exe.jdk, ..\jbr, JDK_HOME, JAVA_HOME.
:: ---------------------------------------------------------------------
SET JRE=

IF NOT "%IDEA_JDK%" == "" (
  IF EXIST "%IDEA_JDK%" SET "JRE=%IDEA_JDK%"
)

SET _JRE_CANDIDATE=
IF "%JRE%" == "" IF EXIST "%APPDATA%\JetBrains\IdeaIC2025.2\idea64.exe.jdk" (
  SET /P _JRE_CANDIDATE=<"%APPDATA%\JetBrains\IdeaIC2025.2\idea64.exe.jdk"
)
IF "%JRE%" == "" (
  IF NOT "%_JRE_CANDIDATE%" == "" IF EXIST "%_JRE_CANDIDATE%" SET "JRE=%_JRE_CANDIDATE%"
)

IF "%JRE%" == "" (
  IF EXIST "%IDE_HOME%\jbr" SET "JRE=%IDE_HOME%\jbr"
)

IF "%JRE%" == "" (
  IF EXIST "%JDK_HOME%" (
    SET "JRE=%JDK_HOME%"
  ) ELSE IF EXIST "%JAVA_HOME%" (
    SET "JRE=%JAVA_HOME%"
  )
)

SET "JAVA_EXE=%JRE%\bin\java.exe"
IF NOT EXIST "%JAVA_EXE%" (
  ECHO ERROR: cannot start IntelliJ IDEA.
  ECHO No JRE found. Please make sure IDEA_JDK, JDK_HOME, or JAVA_HOME point to a valid JRE installation.
  EXIT /B
)

:: ---------------------------------------------------------------------
:: Collect JVM options and properties.
:: ---------------------------------------------------------------------
IF NOT "%IDEA_PROPERTIES%" == "" SET IDE_PROPERTIES_PROPERTY="-Didea.properties.file=%IDEA_PROPERTIES%"

SET IDE_CACHE_DIR=%LOCALAPPDATA%\JetBrains\IdeaIC2025.2

:: <IDE_HOME>\bin\[win\]<exe_name>.vmoptions ...
SET VM_OPTIONS_FILE=
IF EXIST "%IDE_BIN_DIR%\idea64.exe.vmoptions" (
  SET "VM_OPTIONS_FILE=%IDE_BIN_DIR%\idea64.exe.vmoptions"
) ELSE IF EXIST "%IDE_BIN_DIR%\win\idea64.exe.vmoptions" (
  SET "VM_OPTIONS_FILE=%IDE_BIN_DIR%\win\idea64.exe.vmoptions"
)

:: ... [+ %<IDE_NAME>_VM_OPTIONS% || <IDE_HOME>.vmoptions (Toolbox) || <config_directory>\<exe_name>.vmoptions]
SET USER_VM_OPTIONS_FILE=
IF NOT "%IDEA_VM_OPTIONS%" == "" (
  IF EXIST "%IDEA_VM_OPTIONS%" SET "USER_VM_OPTIONS_FILE=%IDEA_VM_OPTIONS%"
)
IF "%USER_VM_OPTIONS_FILE%" == "" (
  IF EXIST "%IDE_HOME%.vmoptions" (
    SET "USER_VM_OPTIONS_FILE=%IDE_HOME%.vmoptions"
  ) ELSE IF EXIST "%APPDATA%\JetBrains\IdeaIC2025.2\idea64.exe.vmoptions" (
    SET "USER_VM_OPTIONS_FILE=%APPDATA%\JetBrains\IdeaIC2025.2\idea64.exe.vmoptions"
  )
)

SET ACC=
SET USER_GC=
SET USER_PCT_INI=
SET USER_PCT_MAX=
SET FILTERS=%TMP%\ij-launcher-filters-%RANDOM%.txt
IF NOT "%USER_VM_OPTIONS_FILE%" == "" (
  SET ACC="-Djb.vmOptionsFile=%USER_VM_OPTIONS_FILE%"
  FINDSTR /R /C:"-XX:\+.*GC" "%USER_VM_OPTIONS_FILE%" > NUL
  IF NOT ERRORLEVEL 1 SET USER_GC=yes
  FINDSTR /R /C:"-XX:InitialRAMPercentage=" "%USER_VM_OPTIONS_FILE%" > NUL
  IF NOT ERRORLEVEL 1 SET USER_PCT_INI=yes
  FINDSTR /R /C:"-XX:M[ia][nx]RAMPercentage=" "%USER_VM_OPTIONS_FILE%" > NUL
  IF NOT ERRORLEVEL 1 SET USER_PCT_MAX=yes
) ELSE IF NOT "%VM_OPTIONS_FILE%" == "" (
  SET ACC="-Djb.vmOptionsFile=%VM_OPTIONS_FILE%"
)
IF NOT "%VM_OPTIONS_FILE%" == "" (
  IF "%USER_GC%%USER_PCT_INI%%USER_PCT_MAX%" == "" (
    FOR /F "eol=# usebackq delims=" %%i IN ("%VM_OPTIONS_FILE%") DO CALL SET ACC=%%ACC%% "%%i"
  ) ELSE (
    IF NOT "%USER_GC%" == "" ECHO -XX:\+.*GC>> "%FILTERS%"
    IF NOT "%USER_PCT_INI%" == "" ECHO -Xms>> "%FILTERS%"
    IF NOT "%USER_PCT_MAX%" == "" ECHO -Xmx>> "%FILTERS%"
    FOR /F "eol=# usebackq delims=" %%i IN (`FINDSTR /R /V /G:"%FILTERS%" "%VM_OPTIONS_FILE%"`) DO CALL SET ACC=%%ACC%% "%%i"
    DEL "%FILTERS%"
  )
)
IF NOT "%USER_VM_OPTIONS_FILE%" == "" (
  FOR /F "eol=# usebackq delims=" %%i IN ("%USER_VM_OPTIONS_FILE%") DO CALL SET ACC=%%ACC%% "%%i"
)
IF "%VM_OPTIONS_FILE%%USER_VM_OPTIONS_FILE%" == "" (
  ECHO ERROR: cannot find a VM options file
)

SET "CLASS_PATH=%IDE_HOME%\lib\platform-loader.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\util-8.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\app-client.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\util.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\app.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\annotations.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\bouncy-castle.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\eclipse.lsp4j.debug.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\eclipse.lsp4j.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\eclipse.lsp4j.jsonrpc.debug.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\eclipse.lsp4j.jsonrpc.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\external-system-rt.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\externalProcess-rt.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\forms_rt.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\groovy.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\idea_rt.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\intellij-test-discovery.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\javax.activation.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\javax.annotation-api.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\jaxb-api.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\jaxb-runtime.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\jps-model.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\jsch-agent.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\kotlinx-coroutines-slf4j-1.10.1-intellij.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\lib-client.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\lib.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\opentelemetry.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\protobuf.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\rd.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\rhino.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\stats.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\trove.jar"
SET "CLASS_PATH=%CLASS_PATH%;%IDE_HOME%\lib\util_rt.jar"

:: ---------------------------------------------------------------------
:: Run the IDE.
:: ---------------------------------------------------------------------
"%JAVA_EXE%" ^
  -cp "%CLASS_PATH%" ^
  "-XX:ErrorFile=%USERPROFILE%\java_error_in_idea_%%p.log" ^
  "-XX:HeapDumpPath=%USERPROFILE%\java_error_in_idea.hprof" ^
  %ACC% ^
  %IDE_PROPERTIES_PROPERTY% ^
  "-Xbootclasspath/a:%IDE_HOME%\lib\nio-fs.jar" -Djava.system.class.loader=com.intellij.util.lang.PathClassLoader -Didea.vendor.name=JetBrains -Didea.paths.selector=IdeaIC2025.2 "-Djna.boot.library.path=%IDE_HOME%/lib/jna/amd64" -Djna.nosys=true -Djna.noclasspath=true "-Dpty4j.preferred.native.folder=%IDE_HOME%/lib/pty4j" -Dio.netty.allocator.type=pooled "-Dintellij.platform.runtime.repository.path=%IDE_HOME%/modules/module-descriptors.dat" -Didea.platform.prefix=Idea -Dwsl.use.remote.agent.for.nio.filesystem=true -Djava.nio.file.spi.DefaultFileSystemProvider=com.intellij.platform.core.nio.fs.MultiRoutingFileSystemProvider -Dsplash=true -Daether.connector.resumeDownloads=false -Dcompose.swing.render.on.graphics=true --add-opens=java.base/java.io=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.lang.ref=ALL-UNNAMED --add-opens=java.base/java.lang.reflect=ALL-UNNAMED --add-opens=java.base/java.net=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/java.nio.charset=ALL-UNNAMED --add-opens=java.base/java.text=ALL-UNNAMED --add-opens=java.base/java.time=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/java.util.concurrent=ALL-UNNAMED --add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED --add-opens=java.base/java.util.concurrent.locks=ALL-UNNAMED --add-opens=java.base/jdk.internal.vm=ALL-UNNAMED --add-opens=java.base/sun.net.dns=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/sun.nio.fs=ALL-UNNAMED --add-opens=java.base/sun.security.ssl=ALL-UNNAMED --add-opens=java.base/sun.security.util=ALL-UNNAMED --add-opens=java.desktop/com.sun.java.swing=ALL-UNNAMED --add-opens=java.desktop/java.awt=ALL-UNNAMED --add-opens=java.desktop/java.awt.dnd.peer=ALL-UNNAMED --add-opens=java.desktop/java.awt.event=ALL-UNNAMED --add-opens=java.desktop/java.awt.font=ALL-UNNAMED --add-opens=java.desktop/java.awt.image=ALL-UNNAMED --add-opens=java.desktop/java.awt.peer=ALL-UNNAMED --add-opens=java.desktop/javax.swing=ALL-UNNAMED --add-opens=java.desktop/javax.swing.plaf.basic=ALL-UNNAMED --add-opens=java.desktop/javax.swing.text=ALL-UNNAMED --add-opens=java.desktop/javax.swing.text.html=ALL-UNNAMED --add-opens=java.desktop/javax.swing.text.html.parser=ALL-UNNAMED --add-opens=java.desktop/sun.awt=ALL-UNNAMED --add-opens=java.desktop/sun.awt.datatransfer=ALL-UNNAMED --add-opens=java.desktop/sun.awt.image=ALL-UNNAMED --add-opens=java.desktop/sun.awt.windows=ALL-UNNAMED --add-opens=java.desktop/sun.font=ALL-UNNAMED --add-opens=java.desktop/sun.java2d=ALL-UNNAMED --add-opens=java.desktop/sun.swing=ALL-UNNAMED --add-opens=java.management/sun.management=ALL-UNNAMED --add-opens=jdk.attach/sun.tools.attach=ALL-UNNAMED --add-opens=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED --add-opens=jdk.internal.jvmstat/sun.jvmstat.monitor=ALL-UNNAMED --add-opens=jdk.jdi/com.sun.tools.jdi=ALL-UNNAMED ^
  com.intellij.idea.Main ^
  %*
