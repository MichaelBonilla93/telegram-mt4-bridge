//+------------------------------------------------------------------+
//|                                              mt4_bridge.mq4       |
//|  Puente por archivos: lee comandos JSON y ejecuta OrderSend.     |
//+------------------------------------------------------------------+
#property strict

input string BridgeFolder = "bridge"; // subcarpeta dentro de MQL4/Files
input int    Slippage     = 30;       // slippage en puntos
input int    MagicNumber  = 770077;

string CmdDir() { return BridgeFolder + "\\commands\\"; }
string RspDir() { return BridgeFolder + "\\responses\\"; }

int OnInit()
{
   EventSetMillisecondTimer(500); // revisar cada 500ms
   Print("mt4_bridge iniciado. Carpeta: ", BridgeFolder);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { EventKillTimer(); }

// Extrae el valor (string) de una clave en un JSON plano.
string JsonStr(string json, string key)
{
   // Incluimos los dos puntos para no hacer match dentro del valor de "comment".
   string pat = "\"" + key + "\":";
   int k = StringFind(json, pat);
   if(k < 0) return "";
   int i = k + StringLen(pat);
   // saltar espacios y comillas de apertura
   while(i < StringLen(json) && (StringGetChar(json,i)==' ' )) i++;
   bool quoted = (StringGetChar(json,i)=='"');
   if(quoted) i++;
   string out = "";
   while(i < StringLen(json))
   {
      int c = StringGetChar(json,i);
      if(quoted && c=='"') break;
      if(!quoted && (c==',' || c=='}')) break;
      out += CharToString((uchar)c);
      i++;
   }
   return out;
}

double JsonNum(string json, string key) { return StringToDouble(JsonStr(json,key)); }

double PipSize(string symbol)
{
   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   double point = MarketInfo(symbol, MODE_POINT);
   // 5 o 3 dígitos => pip = 10 * point; 4 o 2 => pip = point
   if(digits==5 || digits==3) return 10*point;
   return point;
}

void WriteResponse(string fname, string id, bool ok, int ticket, double price, string err)
{
   // Escribimos primero a un .tmp y luego movemos: Python solo ve <id>.json
   // cuando el contenido ya está completo (evita leer una respuesta parcial).
   string tmpName = RspDir()+fname+".tmp";
   int h = FileOpen(tmpName, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) { Print("No pude escribir respuesta ", fname); return; }
   string oks = ok ? "true" : "false";
   string es  = (err=="") ? "null" : "\""+err+"\"";
   string json = StringFormat(
      "{\"id\":\"%s\",\"success\":%s,\"ticket\":%d,\"price\":%.5f,\"error\":%s}",
      id, oks, ticket, price, es);
   FileWriteString(h, json);
   FileClose(h);
   FileMove(tmpName, 0, RspDir()+fname, FILE_REWRITE);
}

void ProcessFile(string fname)
{
   int h = FileOpen(CmdDir()+fname, FILE_READ|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   string json = "";
   while(!FileIsEnding(h)) json += FileReadString(h);
   FileClose(h);

   string id        = JsonStr(json, "id");
   string symbol    = JsonStr(json, "symbol");
   string direction = JsonStr(json, "direction");
   double lot       = JsonNum(json, "lot");
   double sl        = JsonNum(json, "stop_loss");
   double tp        = JsonNum(json, "take_profit");
   double entryRef  = JsonNum(json, "entry_ref");
   double tolPips   = JsonNum(json, "tolerance_pips");
   string comment   = JsonStr(json, "comment");

   int cmd = (direction=="BUY") ? OP_BUY : OP_SELL;
   double price = (cmd==OP_BUY) ? MarketInfo(symbol, MODE_ASK)
                                : MarketInfo(symbol, MODE_BID);

   // Tolerancia: validar con precio en vivo
   double pip = PipSize(symbol);
   double deviation = MathAbs(price - entryRef) / pip;
   if(deviation > tolPips)
   {
      WriteResponse(fname, id, false, 0, price,
         StringFormat("Precio fuera de tolerancia (%.1f pips > %.1f)", deviation, tolPips));
      FileDelete(CmdDir()+fname);
      return;
   }

   int ticket = OrderSend(symbol, cmd, lot, price, Slippage, sl, tp,
                          comment, MagicNumber, 0, clrNONE);
   if(ticket < 0)
      WriteResponse(fname, id, false, 0, price, "OrderSend error " + IntegerToString(GetLastError()));
   else
      WriteResponse(fname, id, true, ticket, price, "");

   FileDelete(CmdDir()+fname);
}

void OnTimer()
{
   string fname;
   long h = FileFindFirst(CmdDir()+"*.json", fname);
   if(h==INVALID_HANDLE) return;
   do {
      if(StringFind(fname, ".tmp") < 0)  // ignorar archivos a medio escribir
         ProcessFile(fname);
   } while(FileFindNext(h, fname));
   FileFindClose(h);
}
//+------------------------------------------------------------------+
