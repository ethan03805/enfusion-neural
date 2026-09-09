// Inspect native containers without modifying them or loading a world.
[WorkbenchPluginAttribute(name: "Enfusion Neural material schema", wbModules: {"ResourceManager"})]
class ENR_MaterialSchemaPlugin : WorkbenchPlugin
{
 void Inspect(BaseContainer container, string path, int depth)
 {
  if (!container || depth > 4) return;
  PrintFormat("ENR_SCHEMA_CONTAINER path=%1 class=%2 fields=%3", path, container.GetClassName(), container.GetNumVars());
  for (int i = 0; i < container.GetNumVars() && i < 256; i++)
  {
   string key = container.GetVarName(i);
   int kind = container.GetDataVarType(i);
   string defaultValue;
   bool hasDefault = container.GetDefaultAsString(key, defaultValue);
   PrintFormat("ENR_SCHEMA_FIELD path=%1 name=%2 type=%3 has_default=%4 default=%5", path, key, kind, hasDefault, defaultValue);
   float number;
   int integer;
   bool flag;
   bool read;
   if (kind == DataVarType.OBJECT) { Inspect(container.GetObject(key), path + "." + key, depth + 1); continue; }
   if (kind == DataVarType.STRING || kind == DataVarType.TEXTURE || kind == DataVarType.RESOURCE_NAME)
   {
    string textValue;
    read = container.Get(key, textValue);
    PrintFormat("ENR_SCHEMA_TEXT path=%1 name=%2 read=%3 value=%4", path, key, read, textValue);
    continue;
   }
   if (kind == DataVarType.COLOR)
   {
    Color colorValue = new Color(0, 0, 0, 0);
    read = container.Get(key, colorValue);
    PrintFormat("ENR_SCHEMA_COLOR path=%1 name=%2 read=%3 rgba=%4 %5 %6 %7", path, key, read, colorValue.R(), colorValue.G(), colorValue.B(), colorValue.A());
    continue;
   }
   if (kind == DataVarType.SCALAR) read = container.Get(key, number);
   else if (kind == DataVarType.INTEGER) { read = container.Get(key, integer); number = integer; }
   else if (kind == DataVarType.BOOLEAN) { read = container.Get(key, flag); number = flag; }
   else continue;
   PrintFormat("ENR_SCHEMA_NUMBER path=%1 name=%2 read=%3 value=%4", path, key, read, number);
  }
 }

 override void RunCommandline()
 {
  Print("ENR_SCHEMA started");
  for (int i = 0; i < ENR_SchemaConfig.Count(); i++)
  {
   string label = ENR_SchemaConfig.Label(i);
   ResourceName resourceName = ENR_SchemaConfig.ResourceAt(i);
   Resource resource = BaseContainerTools.LoadContainer(resourceName);
   if (!resource || !resource.IsValid()) { PrintFormat("ENR_SCHEMA_RESULT name=%1 loaded=0 reason=resource", label); continue; }
   BaseContainer container = resource.GetResource().ToBaseContainer();
   if (!container) { PrintFormat("ENR_SCHEMA_RESULT name=%1 loaded=0 reason=container", label); continue; }
   Inspect(container, label, 0);
   PrintFormat("ENR_SCHEMA_RESULT name=%1 loaded=1 class=%2 fields=%3", label, container.GetClassName(), container.GetNumVars());
  }
  Print("ENR_SCHEMA completed");
  Workbench.Exit(0);
 }
}
