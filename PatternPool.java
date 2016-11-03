import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;

import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;

/**
 * Created by sergeybp on 27.10.16.
 */
public class PatternPool {

    ArrayList<Pattern> patterns;

    PatternPool(String fileName) {
        patterns = new ArrayList<>();
        try {
            readFromExcel(fileName);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    PatternPool(){
        patterns = new ArrayList<>();
    }


    public void readFromExcel(String file) throws IOException {
        XSSFWorkbook myExcelBook = new XSSFWorkbook(new FileInputStream(file));
        XSSFSheet myExcelSheet = myExcelBook.getSheetAt(0);
        Iterator<Row> rowIterator = myExcelSheet.iterator();
        rowIterator.next();
        while (rowIterator.hasNext()) {
            Row row = rowIterator.next();

            Iterator<Cell> cellIterator = row.cellIterator();
            if(!cellIterator.hasNext()){
                return;
            }
            Cell cell = cellIterator.next();
            int id = (int) cell.getNumericCellValue();
            Main.maxID = Math.max(id, Main.maxID);
            cell = cellIterator.next();
            String patternString = cell.getStringCellValue();
            cell = cellIterator.next();
            String arg1_case = cell.getStringCellValue();
            cell = cellIterator.next();
            String arg1_num = cell.getStringCellValue();
            cell = cellIterator.next();
            String arg1_pos = cell.getStringCellValue();
            cell = cellIterator.next();
            String arg2_case = cell.getStringCellValue();
            cell = cellIterator.next();
            String arg2_num = cell.getStringCellValue();
            cell = cellIterator.next();
            String arg2_pos = cell.getStringCellValue();

            PatternTemplateWord arg1 = new PatternTemplateWord(arg1_case, arg1_num, arg1_pos);
            PatternTemplateWord arg2 = new PatternTemplateWord(arg2_case, arg2_num, arg2_pos);

            Pattern pattern = new Pattern(id, patternString, arg1, arg2);

            patterns.add(pattern);

        }
    }

    public Pattern getPatternById(int id){
        for(Pattern pattern: patterns){
            if(pattern.id == id){
                return pattern;
            }
        }
        return null;
    }


    public void addPattern(Pattern pattern){
        patterns.add(pattern);
    }

    public void toJson(String path){
        JSONObject obj = new JSONObject();
        for(int i = 0 ; i < patterns.size(); i ++){
            Pattern pattern = patterns.get(i);
            JSONObject tmp = new JSONObject();
            tmp.put("pattern",pattern.pattern);
            tmp.put("id",pattern.id);
            tmp.put("arg1_case",pattern.arg1.casee);
            tmp.put("arg1_num",pattern.arg1.number);
            tmp.put("arg1_pos",pattern.arg1.pos);
            tmp.put("arg2_case",pattern.arg2.casee);
            tmp.put("arg2_num",pattern.arg2.number);
            tmp.put("arg2_pos",pattern.arg2.pos);

            obj.put(""+i,tmp);
        }
        try {

            FileWriter file = new FileWriter(path);
            file.write(obj.toJSONString());
            file.flush();
            file.close();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

}
