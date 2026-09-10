#ifdef WORKBENCH
class ENR_GeometrySample
{
 int Index;
 vector Pixel;
 vector Start;
 vector Direction;
 vector Projected;
 vector Normal;
 float Fraction;
 float Distance;
 string Mesh;
 string HitMaterial;
 string Collider;
}

class ENR_GeometryProbe
{
 static void Run(BaseWorld world, int width, int height)
 {
  int camera = world.GetCurrentCameraId();
  PrintFormat("ENR_GEOMETRY started width=%1 height=%2 camera=%3 grid=64,36 range=250", width, height, camera);
  for (int mode = 0; mode < 2; mode++)
  {
   for (int pass = 0; pass < 3; pass++)
   {
    ref array<ref ENR_GeometrySample> samples = {};
    int began = System.GetTickCount();
    for (int y = 0; y < 36; y++)
    {
     for (int x = 0; x < 64; x++)
     {
      ENR_GeometrySample sample = new ENR_GeometrySample();
      sample.Index = y * 64 + x;
      // First capture showed integer-pixel unprojection; retain that failure.
      int px = (x + 0.5) * width / 64;
      int py = (y + 0.5) * height / 36;
      sample.Pixel = Vector(px, py, 0);
      vector direction;
      vector start = world.ProjectViewportToWorld(px, py, camera, width, height, direction);
      direction.Normalize();
      sample.Start = start;
      sample.Direction = direction;
      TraceParam param = new TraceParam();
      param.Start = start;
      param.End = start + direction * 250;
      param.Flags = TraceFlags.ENTS | TraceFlags.WORLD;
      if (mode == 1) param.Flags = param.Flags | TraceFlags.VISIBILITY;
      sample.Fraction = world.TraceMove(param, null);
      sample.Distance = param.TraceDist;
      sample.Normal = param.TraceNorm;
      sample.HitMaterial = param.TraceMaterial;
      sample.Collider = param.ColliderName;
      if (param.TraceEnt)
      {
       VObject object = param.TraceEnt.GetVObject();
       if (object) sample.Mesh = object.GetResourceName();
      }
      vector hit = start + direction * (250 * sample.Fraction);
      sample.Projected = world.ProjectWorldToViewport(hit, camera, width, height);
      samples.Insert(sample);
     }
    }
    int elapsed = System.GetTickCount(began);
    PrintFormat("ENR_GEOMETRY_TIME mode=%1 pass=%2 rays=%3 milliseconds=%4", mode, pass, samples.Count(), elapsed);
    if (pass != 0) continue;
    foreach (ENR_GeometrySample result : samples)
    {
     PrintFormat("ENR_RAY mode=%1 index=%2 pixel=%3 start=%4 dir=%5 projected=%6 fraction=%7 distance=%8 normal=%9", mode, result.Index, result.Pixel, result.Start, result.Direction, result.Projected, result.Fraction, result.Distance, result.Normal);
     PrintFormat("ENR_RAY_HIT mode=%1 index=%2 mesh=%3 material=%4 collider=%5", mode, result.Index, result.Mesh, result.HitMaterial, result.Collider);
    }
   }
  }
  Print("ENR_GEOMETRY completed");
 }
}
#endif
